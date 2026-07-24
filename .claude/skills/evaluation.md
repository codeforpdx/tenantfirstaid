# Evaluation

Guide for running, analyzing, and improving LangSmith evaluations. Use the `/langsmith` skills for LangSmith-specific guidance (tracing, datasets, evaluators).

## Account tier check

**Ask the user first:** do you have a free or Plus-tier LangSmith account?

Several features require **Plus**:
- Running experiments from the LangSmith UI (bound evaluators)
- Cloud Studio (browser-based agent testing via a deployed LangGraph endpoint)

**Free-tier users** are directed to CLI-only workflows and `langgraph dev` for Studio.

---

## Setup

```bash
cd backend
cp .env.example .env
# Fill in LANGSMITH_API_KEY, GOOGLE_APPLICATION_CREDENTIALS, and other required vars
```

See `/backend` for the full environment variable reference.

---

## Running evaluations

All commands run from `backend/`.

```bash
# Full dataset evaluation (default: 20 repetitions per scenario)
uv run run-langsmith-evaluation

# Custom label and repetition count
uv run run-langsmith-evaluation \
  --dataset "tenant-legal-qa-scenarios" \
  --experiment "my-experiment" \
  --num-repetitions 10
```

Results appear in the LangSmith dashboard under your dataset's Experiments tab.

**CI/CD caveat:** PRs from forked repos don't have access to `LANGSMITH_API_KEY`, so evaluations cannot run in CI. Run locally before submitting a PR for any change affecting response quality.

---

## Dataset management

All commands run from `backend/`. The JSONL file is the source of truth — always commit it after changes.

```bash
# Push local file to LangSmith (first-time or after editing locally)
uv run langsmith-dataset dataset push \
  dataset-tenant-legal-qa-examples.jsonl tenant-legal-qa-scenarios

# Pull after editing in the browser (overwrites local file)
uv run langsmith-dataset dataset pull \
  tenant-legal-qa-scenarios dataset-tenant-legal-qa-examples.jsonl

# Check for drift between local and remote before pushing/pulling
uv run langsmith-dataset dataset diff \
  dataset-tenant-legal-qa-examples.jsonl tenant-legal-qa-scenarios

# Validate schema before pushing
uv run langsmith-dataset dataset validate \
  dataset-tenant-legal-qa-examples.jsonl
```

### Fine-grained example operations

```bash
# List all examples
uv run langsmith-dataset example list tenant-legal-qa-scenarios

# Append new examples without touching existing ones
uv run langsmith-dataset example append \
  tenant-legal-qa-scenarios new-examples.jsonl

# Remove an example by scenario_id
uv run langsmith-dataset example remove \
  tenant-legal-qa-scenarios 42
```

### Adding examples created in the browser

UI-created examples won't have a `scenario_id`. After pulling, assign the next available integer, fill in required metadata fields (`city`, `state`, `tags`, `dataset_split`), validate, push, and commit.

---

## Interpreting scores

Each example scores 0.0–1.0 per evaluator. Active evaluators:

**Legal Correctness** — Is the legal information accurate under Oregon tenant law?

| Score | Meaning |
|---|---|
| 1.0 | Legally accurate |
| 0.5 | Partially correct or missing nuance |
| 0.0 | Legally wrong or misleading |

**Tone** — Is the response appropriately professional, accessible, and empathetic?

| Score | Meaning |
|---|---|
| 1.0 | Gets the tone right |
| 0.5 | Too formal, too casual, or inconsistent |
| 0.0 | Dismissive, condescending, or inappropriate |

Patterns that fail tone: opening with "As a legal expert...", dense jargon, condescending phrasing.

### Variance and noise

Two independent noise sources affect scores:
- **Agent variance** — the chatbot gives slightly different responses to the same question (LLM temperature > 0)
- **Evaluator variance** — the LLM judge assigns slightly different scores to the same output

To isolate evaluator variance (cheap — no new agent calls):

```bash
uv run measure-evaluator-variance \
  --experiment <experiment-name> \
  --evaluator "legal correctness" \
  -k 5
```

**Decision rules:**

| Observation | Diagnosis | Fix |
|---|---|---|
| Evaluator share < 15% of variance | Agent-side noise | Increase `--num-repetitions` |
| Evaluator share > 40% | Judge stochasticity | Stronger judge model; tighten rubric |
| max σ >> mean σ | Borderline outputs | Add rubric guidance for that failure mode |

**Sample size guidance** (σ_agent ≈ 0.20 typical):

| Repetitions | 95% CI width |
|---|---|
| 10 | ± 0.12 |
| 25 | ± 0.08 |
| 35 | ± 0.07 |
| 50 | ± 0.06 |

To detect a 0.10-point improvement with 80% power, you need ~32 repetitions per scenario.

---

## Diagnosing a specific experiment

Use `/analyze-experiment <experiment-name-or-uuid>` for automated root-cause diagnosis — it runs the full trace investigation workflow and recommends fixes matched to the failure mode (retrieval miss, query too broad, reasoning failure, instruction conflict, confabulation, misleading retrieval).

---

## Editing the system prompt

The system prompt lives in `tenantfirstaid/system_prompt.md`. Two runtime placeholders — `{RESPONSE_WORD_LIMIT}` and `{OREGON_LAW_CENTER_PHONE_NUMBER}` — are substituted at startup. Do not add other `{...}` placeholders.

### Iterating in Studio

**Plus-tier:** LangSmith → Deployments → your deployment → Studio.

**Free-tier:** run `langgraph dev` locally:

```bash
cd backend
uv run langgraph dev [--no-browser]
# Opens http://localhost:2024
```

Note: Safari blocks the `http` redirect — use Chrome or Vivaldi. Use `--no-browser` to suppress auto-open.

In Studio, edit the prompt in the **Configuration panel** sidebar, test by chatting, iterate, then copy the final wording back into `system_prompt.md` and commit.

---

## Editing evaluator rubrics

Rubrics live in `evaluate/evaluators/*.md` (e.g. `legal_correctness.md`, `tone.md`). Edit the markdown file and commit. No Python changes needed.

To test a rubric change without re-running the agent:

```bash
# Quick pass — re-score existing outputs once
uv run measure-evaluator-variance \
  --experiment <experiment-name> \
  --evaluator "legal correctness" \
  -k 1

# Focus on a noisy scenario
uv run measure-evaluator-variance \
  --experiment <experiment-name> \
  --evaluator "legal correctness" \
  --scenario 2 -k 5
```

**Plus-tier only:** bound evaluators in the LangSmith UI. When rubric wording is edited in the browser Playground, pull it back:

```bash
uv run langsmith-dataset prompt list
uv run langsmith-dataset prompt pull tfa-legal-correctness \
  evaluators/legal_correctness.md --dry-run   # review diff first
uv run langsmith-dataset prompt pull tfa-legal-correctness \
  evaluators/legal_correctness.md
git add evaluate/evaluators/legal_correctness.md && git commit -m "update rubric from Prompt Hub"
```

---

## Typical workflows

**Pre-release quality check:**
Run evaluation → review scores in LangSmith UI → if failing, use `/analyze-experiment` → fix system prompt or corpus → re-run.

**Add a test for a known chatbot mistake:**
Write the example (question + reference answer) → append to JSONL → push to LangSmith → run evaluation to confirm it fails → fix the chatbot → confirm it passes → commit JSONL + code fix.

**Improve a reference answer using the browser editor:**
Edit in LangSmith UI → `dataset pull` → `git diff` to review → commit.
