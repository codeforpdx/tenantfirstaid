# Automated Evaluation with LangSmith

## What is this and why does it matter?

The chatbot gives legal information to tenants. Getting that information wrong — citing the wrong statute, misstating a deadline, using a dismissive tone — has real consequences for real people. We need a systematic way to check quality, not just hope spot-checks catch problems.

This system runs a suite of test questions through the chatbot automatically, then uses a second AI model ("LLM-as-a-judge") to score the responses against a known-good reference answer. The result is a pass/fail score for each question, surfaced in an online dashboard.

Think of it like a mock client. You hand the chatbot a question you already know the answer to, and measure whether it gets it right.

---

## Definitions

**RAG (Retrieval-Augmented Generation)**
A technique where the AI looks up relevant documents before writing a response, instead of relying solely on what it learned during training. In this project, "retrieval" means searching Oregon housing law texts; "generation" means composing the answer using those passages. This grounds responses in actual statutes rather than the model's general knowledge.

**Agent**
An AI that can do more than answer in one step — it can decide what tools to use, call them, and use the results to compose a final response. Tenant First Aid's chatbot is an agent: when a question comes in, it decides whether to search the legal corpus (the RAG retrieval tool), fetches relevant statutes, and then writes the response.

**System prompt**
A set of instructions given to the agent before any conversation starts. It defines the agent's role, tone, citation style, and legal guardrails ("you are a tenant rights assistant; always cite Oregon statutes; never give legal advice"). The user never sees it. In this codebase it lives in `tenantfirstaid/system_prompt.md`.

**Prompt** (in the context of evaluations)
The text sent to the AI judge telling it how to evaluate a response. Not to be confused with the system prompt above. An evaluator prompt is constructed from the rubric and the scenario data, and instructs the judge what criteria to apply and what format to return scores in.

**Rubric**
A plain-text document that defines the scoring criteria for one evaluator. It describes what earns a 1.0, 0.5, or 0.0 — for example, a legal correctness rubric says "1.0 = legally accurate; 0.0 = legally wrong or misleading." Rubrics live in `evaluate/evaluators/*.md` so lawyers and non-developers can edit them without touching Python code.

**Evaluator**
A piece of scoring logic that reads the chatbot's response to a scenario and assigns a score between 0.0 and 1.0. There are two kinds: *LLM-as-judge* evaluators use a second AI model guided by a rubric; *heuristic* evaluators use deterministic code (e.g. checking whether a citation link is well-formed). Each evaluator measures one dimension of quality — legal accuracy, tone, citation format, and so on.

**Scenario**
One test case. A scenario contains: the question a tenant asks, city/state context (because tenant law varies by jurisdiction), a reference conversation showing what a correct and well-toned response looks like, and a list of key legal facts the response must get right. Scenarios are the unit of work the evaluators score.

**Dataset**
The full collection of scenarios, stored locally in `evaluate/dataset-tenant-legal-qa-scenarios.jsonl` and uploaded to LangSmith for evaluation runs. The JSONL file in the git repository is the source of truth — the LangSmith copy is a working copy that is synced from it.

**Experiment**
One complete run of the dataset through the chatbot. Each experiment records which version of the code and system prompt was used, the chatbot's response to every scenario, and the evaluator scores. Experiments are compared side-by-side in the LangSmith UI to measure the impact of a code or prompt change.

**Deployment**
A version of the agent hosted in LangSmith Cloud, defined by `backend/langgraph.json`. A deployment is needed to run experiments from the LangSmith browser UI (so LangSmith can send test questions to a live endpoint) and to use Cloud Studio. Local development uses `langgraph dev` instead of a full deployment.

---

```mermaid
flowchart LR
    Q["Test question<br>(from dataset)"]
    Bot["Tenant First Aid<br>chatbot"]
    Judge["AI judge<br>(LLM-as-a-judge)"]
    Ref["Reference answer<br>(written by humans)"]
    Score["Score<br>(0.0 – 1.0)"]

    Q --> Bot
    Bot --> Judge
    Ref --> Judge
    Judge --> Score
```

---

## The dataset — the source of truth

The file `dataset-tenant-legal-qa-scenarios.jsonl` is the authoritative list of test scenarios. Every scenario contains:

- **The question** — exactly what a tenant might type
- **Context** — city and state, because tenant law varies by jurisdiction
- **Reference answer** — a human-verified model conversation showing what a correct, well-toned response looks like
- **Key facts** — the legal facts the response must get right

This file lives in the git repository so that all contributors share the same set of test cases. Changes to scenarios should be committed here, not left only in the cloud.

### What a scenario looks like

```
inputs:   { "query": "My landlord hasn't fixed my heat for two weeks — what can I do?",
            "city": null, "state": "OR" }

outputs:  { "facts":  ["Landlord has failed to repair heating for 14 days",
                       "ORS 90.365 allows rent reduction after 7 days notice"],
            "reference_conversation": [ {human turn}, {bot turn} ] }
```

---

## How data flows through the system

### Running an evaluation

```mermaid
sequenceDiagram
    participant JSONL as dataset .jsonl<br/>(git repo)
    participant LS as LangSmith<br/>(cloud)
    participant Bot as Tenant First Aid<br/>chatbot
    participant Judge as AI judge

    JSONL->>LS: push (one-time setup,<br/>or after editing locally)
    LS->>Bot: send each test question
    Bot->>LS: chatbot response
    LS->>Judge: question + response + reference answer
    Judge->>LS: score (0.0 – 1.0)
    LS->>LS: store results in experiment
```

1. The dataset is uploaded to LangSmith (only needed once, or after changes).
2. LangSmith feeds each test question to the chatbot, one at a time.
3. The chatbot responds just as it would for a real user.
4. LangSmith sends the question, the chatbot's response, and the reference answer to the AI judge.
5. The judge scores the response and LangSmith stores the results.
6. You review scores in the LangSmith dashboard.

### Editing scenarios and keeping the repo in sync

The LangSmith online editor is the most convenient way to refine a reference answer or reword a test question. But edits made in the browser don't automatically flow back into the git repository. The pull step closes that loop.

```mermaid
flowchart TD
    JSONL["dataset-tenant-legal-qa-scenarios.jsonl<br>(git — source of truth)"]
    LS["LangSmith dataset<br>(cloud — working copy)"]
    UI["LangSmith UI<br>(browser editor)"]
    Commit["git commit<br>(shared with team)"]

    JSONL -- "dataset push" --> LS
    LS -- "edit in browser" --> UI
    UI -- "dataset pull" --> JSONL
    JSONL --> Commit
```

**The rule:** anything you change in the browser must be pulled back and committed. The JSONL file is what other contributors see. Run `dataset diff` first to see what changed before overwriting either side.

---

## Setup

1. Sign up for a free account at https://smith.langchain.com/ (Personal workspace is sufficient for running evaluations).
2. Generate an API key from your account settings.
3. Copy `.env.example` to `.env` and fill in the values (see [Environment variables](#environment-variables) for the full list):

```bash
cd backend
cp .env.example .env
# Edit .env with your values
```

---

## Dataset management

All dataset operations go through `langsmith_dataset.py`. Commands below assume you are in the `backend/` directory.

### Initial push (first-time or after local edits)

```bash
uv run langsmith_dataset.py dataset push \
  dataset-tenant-legal-qa-scenarios.jsonl \
  tenant-legal-qa-scenarios
```

Creates the dataset in LangSmith if it doesn't exist, then uploads all scenarios.

### Pull after editing in the browser

```bash
uv run langsmith_dataset.py dataset pull \
  tenant-legal-qa-scenarios \
  dataset-tenant-legal-qa-scenarios.jsonl
```

Overwrites the local file with whatever is currently in LangSmith. Commit the result.

### Validate the local file

```bash
uv run langsmith_dataset.py dataset validate \
  dataset-tenant-legal-qa-scenarios.jsonl
```

Checks every line against the schema before pushing, catching formatting mistakes early.

### Check for content drift between local and remote

```bash
# Show which scenarios differ between the local file and LangSmith
uv run langsmith_dataset.py dataset diff \
  dataset-tenant-legal-qa-scenarios.jsonl \
  tenant-legal-qa-scenarios
```

Reports three categories:

| Symbol | Meaning |
|--------|---------|
| `<` | scenario exists only on the left (would be lost on a pull, missing on a push) |
| `>` | scenario exists only on the right |
| `~` | same `scenario_id` on both sides but content differs — shows a field-level unified diff |

Example output:

```
< scenario_id=5
~ scenario_id=12  [content differs]
  --- left/outputs
  +++ right/outputs
  @@ -3,7 +3,7 @@
       "facts": [
  -      "ORS 90.365 allows rent reduction after 7 days notice",
  +      "ORS 90.365 allows rent reduction after 7 days written notice",
         "Landlord must repair within reasonable time"
       ],
> scenario_id=18
```

`dataset diff` is the right first step before pushing or pulling — it tells you exactly what would change. Content changes (`~`) require a human decision: use `scenario update` to push a local fix to LangSmith, or `dataset pull` followed by `git diff` to review before accepting a remote edit.

---

### Fine-grained scenario operations

```bash
# List all scenarios (shows scenario_id, tags, and the first 80 characters of the question)
uv run langsmith_dataset.py scenario list tenant-legal-qa-scenarios

# Append new scenarios from a JSONL file without touching existing ones
uv run langsmith_dataset.py scenario append \
  tenant-legal-qa-scenarios new-scenarios.jsonl

# Remove a scenario by its scenario_id
uv run langsmith_dataset.py scenario remove \
  tenant-legal-qa-scenarios 42
```

---

## Running evaluations

```bash
cd backend/evaluate

# Run evaluation on the full dataset
uv run run_langsmith_evaluation.py

# Run with a custom experiment label (useful for comparing before/after a change)
uv run run_langsmith_evaluation.py \
  --dataset "tenant-legal-qa-scenarios" \
  --experiment "my-experiment" \
  --num-repetitions 1
```

Results appear in the LangSmith dashboard under your dataset's Experiments tab.

### CI/CD

PRs from forked repos don't have access to repository secrets (including `LANGSMITH_API_KEY`), so evaluations cannot run automatically in CI. Run evaluations locally before submitting a pull request for any change that might affect response quality.

---

## What the scores mean

Each scenario gets a score between 0.0 and 1.0 for each active evaluator. The overall pass rate is the average across all scenarios.

### Legal Correctness

Is the legal information accurate under Oregon tenant law?

| Score | Meaning |
|-------|---------|
| 1.0 | Legally accurate |
| 0.5 | Partially correct or missing important nuance |
| 0.0 | Legally wrong or misleading |

### Tone

Is the response appropriately professional, accessible, and empathetic?

| Score | Meaning |
|-------|---------|
| 1.0 | Gets the tone right |
| 0.5 | Too formal, too casual, or inconsistent |
| 0.0 | Dismissive, condescending, or inappropriate |

**Patterns that fail tone evaluation:**
- Opening with "As a legal expert..." (implies the chatbot is giving legal advice, which it isn't)
- Dense legal jargon without plain-language explanation
- Dismissive or condescending phrasing

### Under construction 🚧

These evaluators exist in the code but are disabled pending calibration: citation accuracy, citation format, completeness, tool usage, performance.

---

## How the judge sees each scenario

When the AI judge scores a response, it receives:

```mermaid
flowchart LR
    subgraph "What the judge receives"
        I["inputs<br>(question, city, state)"]
        O["chatbot outputs<br>(response text, reasoning,<br>system prompt)"]
        R["reference outputs<br>(facts, reference conversation)"]
    end
    I --> Verdict
    O --> Verdict
    R --> Verdict
    Verdict["Score + rationale"]
```

The judge compares what the chatbot actually said against what it should have said, given the same question and context.

---

## Viewing and comparing results

Open https://smith.langchain.com/ → your dataset → **Experiments** tab.

From there you can:
- See per-scenario scores and the judge's written rationale for each score
- Compare two experiments side-by-side to measure the impact of a code change
- Filter to failing scenarios to understand where the chatbot struggles

To compare two experiments from the command line:

```bash
uv run python evaluate/langsmith_dataset.py experiment compare \
  tfa-baseline tfa-my-experiment
```

---

## Typical workflows

### "I want to check quality before a release"

```mermaid
flowchart LR
    A["Run evaluation<br>run_langsmith_evaluation.py"] --> B["Review scores<br>in LangSmith UI"]
    B --> C{Passing?}
    C -- Yes --> D["Ship it"]
    C -- No --> E["Investigate failing<br>scenarios in UI"]
    E --> F["Fix chatbot code<br>or system prompt"]
    F --> A
```

### "I found a chatbot mistake and want to add a test for it"

```mermaid
flowchart LR
    A["Write the scenario<br>(question + reference answer)"]
    B["Append to JSONL<br>scenario append"]
    C["Push to LangSmith<br>dataset push"]
    D["Run evaluation<br>to confirm it fails"]
    E["Fix the chatbot"]
    F["Run evaluation<br>to confirm it passes"]
    G["Commit JSONL + code fix"]

    A --> B --> C --> D --> E --> F --> G
```

### "I want to improve a reference answer using the browser editor"

```mermaid
flowchart LR
    A["Edit in<br>LangSmith UI"] --> B["Pull back<br>dataset pull"]
    B --> C["Review diff<br>in git"]
    C --> D["Commit<br>updated JSONL"]
```

---

## Environment variables

The agent needs the same set of variables regardless of where it runs. How you provide them differs between local development and Cloud deployment.

### Variable reference

| Variable | Required | Example | Description |
|---|---|---|---|
| `MODEL_NAME` | yes | `gemini-2.5-pro` | LLM model name |
| `GOOGLE_CLOUD_PROJECT` | yes | `tenantfirstaid` | GCP project ID |
| `GOOGLE_CLOUD_LOCATION` | yes | `global` | Vertex AI location |
| `GOOGLE_APPLICATION_CREDENTIALS` | yes | *(see below)* | GCP credentials — file path locally, inline JSON in Cloud |
| `VERTEX_AI_DATASTORE` | yes | `tenantfirstaid-corpora_...` | Vertex AI Search datastore ID |
| `LANGSMITH_API_KEY` | for evals | `lsv2_pt_...` | LangSmith API key (not needed for `langgraph dev` itself) |
| `LANGSMITH_TRACING` | no | `true` | Enable LangSmith tracing |
| `LANGCHAIN_TRACING_V2` | no | `true` | Enable detailed tracing |
| `LANGSMITH_PROJECT` | no | `tenant-first-aid-dev` | LangSmith project name for traces |
| `SHOW_MODEL_THINKING` | no | `false` | Capture Gemini reasoning in responses |

### Local development (`langgraph dev` and evaluations)

All variables go in `backend/.env`. Copy `.env.example` and fill in the values:

```bash
cp .env.example .env
```

`GOOGLE_APPLICATION_CREDENTIALS` is the **file path** to your GCP credentials JSON, typically `~/.config/gcloud/application_default_credentials.json`. See the project README for how to set up GCP credentials locally.

### LangSmith Cloud deployment

Cloud deployments don't use a `.env` file. Instead, environment variables are configured in the LangSmith UI.

**Setting up the GCP credential as a workspace secret:**

`GOOGLE_APPLICATION_CREDENTIALS` contains sensitive service account JSON. To avoid exposing it in the deployment settings (which are viewable by all workspace members):

1. Go to **LangSmith → Settings → Workspace Secrets**.
2. Create a secret named `GOOGLE_APPLICATION_CREDENTIALS` with the full JSON content of the service account key file (paste the raw JSON, not a file path).
3. Save.

**Configuring the deployment's environment:**

1. Go to **Deployments → your deployment → Settings → Environment Variables**.
2. Add each variable. For most, paste the value directly:

   | Key | Value |
   |---|---|
   | `MODEL_NAME` | `gemini-2.5-pro` |
   | `GOOGLE_CLOUD_PROJECT` | `tenantfirstaid` |
   | `GOOGLE_CLOUD_LOCATION` | `global` |
   | `VERTEX_AI_DATASTORE` | `tenantfirstaid-corpora_...` |
   | `SHOW_MODEL_THINKING` | `false` |

3. For the credential, reference the workspace secret instead of pasting the value:

   | Key | Value |
   |---|---|
   | `GOOGLE_APPLICATION_CREDENTIALS` | `{{GOOGLE_APPLICATION_CREDENTIALS}}` |

   The `{{...}}` syntax tells LangSmith to resolve the value from the workspace secret at runtime. If you later rotate the credential, update the workspace secret — no redeployment needed.

4. Save and redeploy.

`LANGSMITH_API_KEY` is **not** needed in the deployment environment — the Cloud runtime provides it automatically.

---

## Troubleshooting

### "Dataset not found"

The dataset hasn't been pushed yet. Run:
```bash
uv run langsmith_dataset.py dataset push \
  dataset-tenant-legal-qa-scenarios.jsonl \
  tenant-legal-qa-scenarios
```

### Scores seem wrong or inconsistent

LLM-as-judge has its own biases and can be inconsistent on borderline cases. Review the judge's written rationale for specific failing scenarios in the LangSmith UI, then refine the evaluator rubrics in `evaluators/*.md` if the scoring logic is the problem (see [Editing evaluator rubrics](#editing-evaluator-rubrics) below).

### Evaluation is too slow

Pass `--max-concurrency 3` (or higher) to run multiple scenarios in parallel, or temporarily reduce the dataset size in LangSmith to evaluate a representative subset.

## Editing the system prompt

The chatbot's system prompt lives in `tenantfirstaid/system_prompt.md`. This is a plain-text markdown file that anyone can edit — no Python knowledge required. It controls the chatbot's personality, tone, citation style, and legal guardrails.

The file uses two placeholders that are substituted at runtime:
- `{RESPONSE_WORD_LIMIT}` — currently 350
- `{OREGON_LAW_CENTER_PHONE_NUMBER}` — currently 888-585-9638

Everything else is literal text. **Do not** add other `{...}` placeholders — Python's `str.format()` will break on stray curly braces.

### Iterating on the system prompt in Studio

You don't have to commit every tweak to test it. LangGraph Studio (available via Cloud deployment or `langgraph dev`) exposes the system prompt in a **:gear: Manage Assistants** panel next to the chat window. The full prompt from `system_prompt.md` is pre-populated as the default — you just edit in place and chat.

```mermaid
flowchart LR
    A["Open Studio"] --> B["Edit prompt in<br>Configuration panel"]
    B --> C["Chat with<br>the agent"]
    C --> D{Happy?}
    D -- No --> B
    D -- Yes --> E["Copy final prompt<br>into system_prompt.md"]
    E --> F["Commit & push"]
    F --> G["Run evaluation<br>to confirm"]
```

Step by step:

1. **Open Studio.** Either open LangSmith Cloud → Deployments → your deployment → Studio, or run `langgraph dev` locally and open `http://localhost:2024`.
2. **Find the Configuration panel.** It's in the sidebar or top bar, depending on your Studio version. You'll see a text field labeled **system_prompt** with the full current prompt.
3. **Edit the prompt.** Change whatever you want — rephrase a rule, add a guideline, adjust the tone. The edit applies immediately to the next message you send.
4. **Chat with the agent.** Send a test question and see how the agent responds with your updated prompt. Try several questions to check different behaviors.
5. **Iterate.** Tweak the prompt again, send another question. Repeat until you're satisfied. Each conversation thread remembers your config, so you can go back and compare.
6. **Save your work.** Once you have wording you like, copy the prompt text from the Configuration panel and paste it into `tenantfirstaid/system_prompt.md` (remember to keep the `{RESPONSE_WORD_LIMIT}` and `{OREGON_LAW_CENTER_PHONE_NUMBER}` placeholders). Commit and push.
7. **Run an evaluation** to verify the change didn't break anything across the full scenario suite.

The Configuration panel is per-conversation — resetting it or starting a new thread reverts to the default from `system_prompt.md`. Your changes aren't permanent until you commit the file.

---

## Editing evaluator rubrics

LLM-as-judge evaluators (legal correctness, tone, citation accuracy) use scoring rubrics stored as markdown files in `evaluators/`:

```
evaluators/
  legal_correctness.md
  tone.md
  citation_accuracy.md
```

Each file describes what a good answer looks like and the scoring guidelines (1.0 / 0.5 / 0.0). The Python code in `langsmith_evaluators.py` loads these files and wraps them in the structural boilerplate the AI judge needs.

To refine how the judge scores responses, edit the rubric file and commit. You can also experiment with rubric wording in the LangSmith UI by binding an LLM-as-judge evaluator to your dataset — when you find wording you like, copy it back into the `.md` file and commit so everyone shares the same criteria.

Heuristic evaluators (citation format, tool usage, performance) are Python code in `langsmith_evaluators.py` and require a developer to modify.

---

## Bound evaluators (running evaluations from the LangSmith UI)

Instead of running `run_langsmith_evaluation.py` locally, you can bind an LLM-as-judge evaluator directly to the dataset in LangSmith and run experiments from the browser against your Cloud deployment. This is useful for non-developers who want to iterate on the system prompt or test scenarios without a local Python setup.

### How it works

```mermaid
sequenceDiagram
    participant UI as LangSmith UI
    participant DS as Dataset<br/>(tenant-legal-qa-scenarios)
    participant Deploy as Cloud deployment<br/>(LangGraph)
    participant Judge as Bound evaluator<br/>(LLM-as-judge)

    UI->>DS: start experiment
    DS->>Deploy: send each test question
    Deploy->>DS: chatbot response
    DS->>Judge: inputs + outputs + reference outputs
    Judge->>DS: score (0.0 – 1.0)
    UI->>UI: display results in Experiments tab
```

### Prerequisites

- A LangSmith **Plus-tier** seat (bound evaluators are not available on the free tier).
- The dataset `tenant-legal-qa-scenarios` already pushed to LangSmith (see [Dataset management](#dataset-management)).
- A working Cloud deployment of the agent (see [Testing the agent with LangGraph Studio → Option A](#option-a-langsmith-cloud-plus-tier-seat-holders)).

### Setting up a bound evaluator (example: Legal Correctness)

1. Go to **LangSmith → Datasets → `tenant-legal-qa-scenarios`**.
2. Open the **Evaluators** tab and click **+ Add Evaluator**.
3. Choose **LLM-as-Judge**.

#### Prompt

Choose **Create your own prompt** and paste the contents of `evaluators/legal_correctness.md` wrapped in the boilerplate from `langsmith_evaluators.py:load_rubric`. Three placeholder variables — `{inputs}`, `{outputs}`, `{reference_outputs}` — are populated automatically by LangSmith from the dataset example and the deployment's response.

**Prompt commits.** Every time you save or edit the prompt, LangSmith creates a new commit with a unique hash, giving you a version history you can browse and revert.

#### Model configuration

Select the model the judge will use. To match the offline evaluator, use:

| Setting | Value | Notes |
|---|---|---|
| **Provider** | `Cloud providers: Google Vertex AI` | Routes judge calls through Vertex AI using the workspace provider secret. |
| **API Key Name** | `GOOGLE_VERTEX_AI_WEB_CREDENTIALS` | The provider secret defined in **Settings → Workspace → Integrations → Provider secrets**. This is the same service account credential as `GOOGLE_APPLICATION_CREDENTIALS`, registered under the name LangSmith expects for Vertex AI. |
| **Model** | `gemini-2.5-flash` | Matches `EVALUATOR_MODEL_NAME` in `langsmith_evaluators.py`. |
| **Temperature** | `0.0` | Lower temperature = more deterministic scoring. The offline `openevals` evaluator defaults to `0.0`. |

#### Feedback configuration

Feedback configuration defines the scoring rubric the judge outputs. Scores are attached as feedback to each run in the experiment.

| Setting | Value | Notes |
|---|---|---|
| **Feedback key** | `legal correctness` | The name shown in experiment results. Use the same key as the offline evaluator so scores are comparable across UI and CLI experiments. |
| **Description** | `Is the legal information accurate under Oregon tenant law?` | Optional but helpful for collaborators. |
| **Feedback type** | **Continuous** | Numerical score within a range. The other options are **Boolean** (true/false) and **Categorical** (predefined labels). |
| **Range** | `0.0` – `1.0` | Matches the offline evaluator's three-level scale (0.0 / 0.5 / 1.0). |

LangSmith adds the feedback configuration as structured output instructions to the judge prompt behind the scenes, so the model knows what format to return.

#### Save

Click **Save**. The evaluator is now bound to the dataset and will automatically run on any new experiment created against this dataset — whether started from the UI or from the SDK.

#### Adding the tone evaluator

Repeat the steps above using the rubric from `evaluators/tone.md`, feedback key `appropriate tone`, and the same prompt template structure.

### Running an experiment from the UI

1. Go to the dataset's **Experiments** tab.
2. Click **+ New Experiment**.
3. Select your **Cloud deployment** as the target.
4. Run. LangSmith sends each dataset example to the deployment, collects responses, and scores them with the bound evaluator automatically.

Results appear in the same Experiments view used by the offline CLI, with the same feedback keys, so scores are directly comparable.

#### How the deployment accepts dataset inputs

The dataset stores scenarios as `query/state/city`, but the underlying agent expects a `messages` list. The deployment graph has an adapter node that converts `query` to a `HumanMessage` before the agent runs, so dataset examples are sent directly to the deployment without any transformation on the LangSmith side. The deployment's input schema (`_DeploymentInput` in `graph.py`) declares `query` and `state` as required and `city` as optional, matching the dataset format.

### Keeping bound evaluators in sync with the codebase

There is no API to update a bound evaluator prompt programmatically. When you edit a rubric in `evaluators/`, update the bound evaluator prompt manually in the LangSmith UI (Datasets → `tenant-legal-qa-scenarios` → Evaluators → edit the evaluator).

If a lawyer edits the rubric wording in the LangSmith Playground, pull the changes back to the local files. First check what changed with a dry run:

First, find the prompt name:

```bash
uv run langsmith_dataset.py prompt list
```

Then dry-run to review the diff:

```bash
uv run langsmith_dataset.py prompt pull tfa-legal-correctness evaluators/legal_correctness.md --dry-run
```

Then write and commit:

```bash
uv run langsmith_dataset.py prompt pull tfa-legal-correctness evaluators/legal_correctness.md
git add evaluate/evaluators/legal_correctness.md
git commit -m "update legal correctness rubric from Prompt Hub"
```

This only works if the prompt uses `<Rubric>…</Rubric>` tags around the rubric text.

### Cost

Bound evaluators use your GCP service account (`GOOGLE_VERTEX_AI_WEB_CREDENTIALS`) to call the judge model on Vertex AI. Judge model calls are billed to your Google Cloud account, not your LangSmith plan.

---

## Testing the agent with LangGraph Studio

Studio lets you chat with the full agent — tools, RAG retrieval, and all — in an interactive UI. There are two ways to access it depending on your setup.

### Option A: LangSmith Cloud (Plus-tier seat holders)

No local setup needed. Go to LangSmith → Deployments → your deployment → **Studio**. The agent is deployed from the `langgraph.json` manifest in `backend/`, and environment variables are configured in the deployment settings (see [Environment variables → LangSmith Cloud deployment](#langsmith-cloud-deployment) above).

Cloud deployment also enables:
- **Bound evaluators**: LLM-as-judge evaluators configured in the UI that auto-run on new experiments
- **Experiment comparison**: side-by-side scoring across prompt or code changes

### Option B: Local dev server (no LangSmith account required)

For contributors without a Plus-tier seat, `langgraph dev` runs the same agent locally.

```bash
cd backend
uv run langgraph dev [--no-browser]
```

This starts a local server on `http://localhost:2024` with an interactive Studio UI. You can chat with the agent, see tool calls and RAG results, inspect the graph execution step by step, and use the Configuration panel to iterate on the system prompt — the same workflow as Cloud Studio.

Requires `langgraph-cli[inmem]` (already in dev dependencies) and GCP credentials in your local `.env`.

**NOTE**: Safari blocks the `http` redirect, so use Vivaldi/Chrome (`--no-browser` runs without automatically opening up your default browser ... navigate to the `Studio UI` URL)

---

## Roadmap

- [x] demonstrate basic evaluation flow (CLI-only) on single-turn scenarios
- [x] use LangSmith web UI to view experimental results
- [x] capture more info in LangSmith experimental results to enable debugging (aka LLM psycho-analysis)
- [x] externalize system prompt to editable markdown file
- [x] externalize evaluator rubrics to editable markdown files
- [x] LangGraph entry point for `langgraph dev` and Cloud deployment
- [x] configurable system prompt in LangGraph Studio (no redeploy needed to iterate)
- [ ] enable additional evaluators (e.g. citation correctness)
- [ ] enable LangSmith web UI to edit scenarios
  - [ ] update facts in existing scenarios to enable additional/better evaluators (e.g. citation correctness)
- [x] enable LangSmith web UI to edit evaluators via bound evaluators
- [x] enable LangSmith web UI to launch experiments via Cloud deployment
- [ ] demonstrate evaluation of multi-turn scenarios
- [ ] A/B testing of system prompt variants
