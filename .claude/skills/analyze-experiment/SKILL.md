# Analyze LangSmith Experiment

Analyze an evaluation experiment using the `langsmith_dataset` CLI.
The argument is an experiment name or UUID (e.g. `/analyze-experiment tfa-2026-04-13` or `/analyze-experiment c663e09e-...`).

## Instructions

The CLI entry point is:
```
uv run python -m evaluate.langsmith_dataset <noun> <verb> [args]
```
Run all CLI commands from `backend/` with `dangerouslyDisableSandbox: true` (requires network access to LangSmith).

### Step 1 — Overview

Run these two commands in parallel:

```
experiment stats <experiment> --evaluator "legal correctness"
history baseline
```

The stats table shows per-scenario means and σ — note low means and high variance. The scenario-id is the integer in brackets, e.g. `[3]` → `3`.

`history baseline` prints the best prior clean-commit history entry to use as a regression reference. If a baseline exists, compare the new experiment's per-scenario means against it and flag any scenario that dropped by more than its baseline σ as a potential regression before proceeding.

### Step 2 — Triage failures by root cause

For each scenario with 0.0 or 0.5 runs, fetch evaluator feedback for **all** failing runs in parallel:

```
runs feedback <uuid>
```

Read the judge comments and bucket each run into a preliminary root-cause category (retrieval miss, reasoning failure, confabulation, citation imprecision, procedural incompleteness, etc.). Note which failure modes are consistent across runs vs. one-offs — consistent patterns are the priority targets and may share a single fix. One-off failures may warrant a separate trace analysis.

If the feedback comments alone don't clearly distinguish root causes (e.g. all comments say "omits delivery requirements" but it's unclear whether retrieval or reasoning is at fault), proceed to Step 3 to resolve the ambiguity with trace evidence.

### Step 3 — Pick exemplars and analyze traces

For each distinct failure bucket identified in Step 2, pick one representative failing run and one 1.0 run from the same scenario. Use `runs exemplars` to get UUIDs sorted worst-to-best:

```
runs exemplars <experiment> <scenario-id> --evaluator "<key>"
```

Run `runs trace <uuid> --verbose` on each pair in parallel.

For each trace, extract:
- **Model thinking**: the `thinking` field inside AIMessage content blocks — read this first. It is the most direct evidence for distinguishing failure modes: confabulation shows up as the model stating a rule in its thinking with no retrieved text supporting it; reasoning failure shows the model correctly identifying the relevant passage in its thinking but misapplying it in the output; retrieval miss shows the model noting uncertainty or falling back to general knowledge because the retrieved passages lacked the relevant statute.
- **RAG queries**: the `query` arg and `max_documents` passed to `retrieve_city_state_laws` on each call
- **Retrieved passages**: the tool response text — look for the specific statutory language the correct answer requires
- **Model output**: the final answer text

If the traces don't resolve the root cause, fetch additional feedback with `runs feedback <uuid>` for the judge's reasoning.

After analyzing traces, **loop back to Step 2** to update or confirm your root-cause buckets before proceeding. Repeat until each failure bucket has a confident root-cause assignment.

### Step 4 — Synthesize

Compare failing and passing traces within each bucket and identify which failure mode applies:

| Mode | Signature |
|------|-----------|
| **Retrieval miss** | Relevant statutory text absent from retrieved passages in both runs; 1.0 run succeeded on different legal reasoning or parametric knowledge |
| **Query too broad** | RAG query echoes the user's words verbatim; specific statute language absent from results |
| **Reasoning failure** | Correct text retrieved but model ignored or misapplied it |
| **Instruction conflict** | Two system-prompt rules contradict; model follows one and suppresses the other |
| **Confabulation** | Model asserted specific numbers/dates/rules not present in retrieved text or system prompt |
| **Misleading retrieval** | Retrieved passages are technically accurate but framed in a way that leads to wrong inference (e.g. perpetrator-liability clause mistaken for victim-liability) |

### Step 5 — Recommend fixes

For each confirmed root cause:
- **Retrieval miss** → corpus update needed; name the missing statute
- **Query too broad** → suggest a better RAG query formulation or update the tool description
- **Reasoning failure** → add a **Clarification** to the system prompt targeting that reasoning step
- **Instruction conflict** → identify the conflicting lines; add a carve-out or clarify precedence
- **Confabulation** → tighten the anti-hallucination instruction or add a **Clarification**
- **Misleading retrieval** → add a system-prompt trigger to search for the protective/corrective statute before drawing conclusions (e.g. "when DV is mentioned, always search ORS 90.453–90.459")

### System-prompt fix conventions

The `### Oregon statute knowledge` section uses two distinct entry types — use the right one:

| Type | Keyword | When to use | Content |
|------|---------|-------------|---------|
| **STOPGAP** | `STOPGAP —` | Corpus retrieval problem: the statute is in the corpus but is mangled (mojibake, chunked away, truncated) so the model can't see it at query time. Provides the text the retriever should have returned. | Direct quotes from the source corpus only — no interpretation, no paraphrase. Sub-bullets may quote additional subsections. These entries are temporary and should be removed once the data store is fixed. |
| **Clarification** | `Clarification —` | Model reasoning problem: the text is retrievable but the model consistently misapplies, misattributes, or omits it. Corrects a wrong belief or fills a persistent reasoning gap. | Interpretive guidance — what the rule means, which subsection governs, what must be included alongside it. |

Never mix the two in a single entry. If a STOPGAP entry contains an interpretive sentence (e.g. "A notice served before the fifth day is premature and legally defective"), split it into a separate Clarification bullet.

### Step 6 — Update eval history

After completing analysis and recommendations, update the history entry for this experiment:

```
history find <experiment>          # get the path
history append <experiment> --section triage --content "<markdown>"
history append <experiment> --section hypotheses --content "<markdown>"
```

The triage content should be the per-scenario failure bucket table from Step 2. The hypotheses content should list each recommended fix with its target failure mode and the scenario(s) it addresses — one hypothesis per bullet, written as a falsifiable prediction: "Adding Clarification X should resolve the procedural-incompleteness failures in S0 (6/12 runs)."

Present findings as: overview table (with baseline delta if available) → per-scenario failure buckets → root-cause diagnosis (with trace evidence) → recommended fixes, in that order.
