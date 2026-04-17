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

Run `experiment stats <experiment> --evaluator "legal correctness"` (or whichever evaluator is of interest) to get per-scenario consistency tables.

The scenario-id is the integer in brackets, e.g. `[3]` → `3`. Note which scenarios have low mean scores or high variance — those are the priority targets.

### Step 2 — Pick exemplars

For the worst-performing scenario and evaluator, run:

```
runs exemplars <experiment> <scenario-id> --evaluator "<key>"
```

This prints all runs for that scenario sorted worst-to-best, with UUIDs and a query preview. Pick one 0.0 run and one 1.0 run from the output — they are guaranteed to be from the same scenario, so the comparison is controlled.

### Step 3 — Trace analysis

Run `runs trace <uuid> --verbose` on each exemplar in parallel.

For each trace, extract:
- **RAG queries**: the `query` arg and `max_documents` passed to `retrieve_city_state_laws` on each call
- **Retrieved passages**: the tool response text — look for the specific statutory language the correct answer requires
- **Model output**: the final answer text
- **Evaluator comment**: run `runs feedback <uuid>` if you need the judge's reasoning

### Step 4 — Synthesize

Compare the 0.0 and 1.0 traces and identify which failure mode applies:

| Mode | Signature |
|------|-----------|
| **Retrieval miss** | Relevant statutory text absent from retrieved passages in both runs; 1.0 run succeeded on different legal reasoning or parametric knowledge |
| **Query too broad** | RAG query echoes the user's words verbatim; specific statute language absent from results |
| **Reasoning failure** | Correct text retrieved but model ignored or misapplied it |
| **Instruction conflict** | Two system-prompt rules contradict; model follows one and suppresses the other |
| **Confabulation** | Model asserted specific numbers/dates/rules not present in retrieved text or system prompt |
| **Misleading retrieval** | Retrieved passages are technically accurate but framed in a way that leads to wrong inference (e.g. perpetrator-liability clause mistaken for victim-liability) |

Then recommend the appropriate fix:
- **Retrieval miss** → corpus update needed; name the missing statute
- **Query too broad** → suggest a better RAG query formulation or update the tool description
- **Reasoning failure** → add system-prompt guidance targeting that reasoning step
- **Instruction conflict** → identify the conflicting lines; add a carve-out or clarify precedence
- **Confabulation** → tighten the anti-hallucination instruction or add a STOPGAP note
- **Misleading retrieval** → add a system-prompt trigger to search for the protective/corrective statute before drawing conclusions (e.g. "when DV is mentioned, always search ORS 90.453–90.459")

Present findings as: overview table → worst-scenario highlights → root-cause diagnosis → recommended fixes, in that order.
