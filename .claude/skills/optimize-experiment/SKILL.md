# Optimize Experiment

Reduce system-prompt token usage and retrieval latency without regressing quality scores. Run this after scores are stable — not during active failure investigation.

The argument is a recent passing experiment to use as a baseline (e.g. `/optimize-experiment extractive-segments-plus-clarifications-IV-83bcb22b`).

There are three optimization targets, ordered by impact. Each targets a different layer of the defense-in-depth stack (see [[defense-in-depth-retrieval-reasoning]]).

---

## Use case 1 — L1/L2 corpus and retrieval improvements

The highest-leverage optimization: fix retrieval gaps at the data-store level so STOPGAPs (L3 compensations) become unnecessary. Every STOPGAP removed reduces tokens on every request.

**L1 — Section-aware chunking:** the current retrieval failures for ORS 90.325 (0/4) and ORS 90.425 (2/4) are chunking problems — the operative subsection lands in a different chunk from the query-attracting catchline. The fix is to reindex with section-boundary-aware chunks that keep each ORS section's catchline + operative subsections together. See GitHub issue #372.

**L2b — Citation-graph follower node:** a LangGraph node that scans retrieved text for embedded ORS citations and eagerly fetches cited sections in parallel. Addresses cross-section reference gaps without adding system-prompt entries. Not yet implemented — see [[defense-in-depth-retrieval-reasoning]] Layer 2b.

**How to measure L1/L2 impact:** `runs stopgap-check <experiment>` runs two checks in sequence:

1. **L1/L2 trace check** (free — reads LangSmith trace data): for each STOPGAP, checks whether its verbatim target text appeared in the passages retrieved during the experiment. The sampling unit is the *repetition* (root run): a repetition counts as a hit if any of its RAG calls returned the target. The denominator is restricted to repetitions of examples whose `facts` mention that statute's ORS number, so it reflects only scenarios that actually exercise the statute. Reports one of: `retirement candidate` (hit in every relevant repetition), `partially retrieved`, or `never retrieved`. A STOPGAP that is doing its job by suppressing retrieval shows up as `no relevant scenarios found` (the model answered from the prompt and never called the tool) — that is a coverage gap, not a pass, and must be resolved with check #2.

2. **Vertex AI re-query** (live retrieval calls): re-queries the *current* retrieval system with the real production queries from the experiment, reporting current hit rate. This only adds information when the datastore differs from the one the trace recorded, so it is **skipped automatically** unless one of these holds: the datastore was reindexed after the experiment ran (confirms the corpus fix is live), check #1 reported a coverage gap (so it can probe the retriever directly, bypassing the agent's decision not to retrieve), or you pass `--force-requery`. For an unchanged datastore that the experiment already exercised, check #1 alone is sufficient and the re-query would just reproduce the trace at the cost of live calls. The skip compares the datastore's last reindex time against the experiment's run time; if either can't be determined it falls open and re-queries.

```bash
cd backend
# Against a recent experiment:
uv run langsmith-dataset runs stopgap-check <baseline-experiment>

# Ad-hoc (Vertex AI re-query only — no trace check):
uv run langsmith-dataset runs stopgap-check \
  --query "tenant liability for damages caused by domestic violence perpetrator" \
  --query "landlord requirements for handling tenant abandoned personal property"
```

A STOPGAP showing `retirement candidate` in the trace check AND N/N in the Vertex AI re-query is ready for Use case 2.

---

## Use case 2 — L3 system-prompt size reduction

**STOPGAP retirement:** after a corpus fix moves a STOPGAP's hit rate to N/N, remove the STOPGAP entry from `system_prompt.md`, run a new experiment, and confirm scores hold. If scores drop, the corpus fix hasn't fully landed — restore the STOPGAP.

**Clarification pruning:** Clarifications that target a failure mode that hasn't appeared in the last 2–3 experiments at 10 repetitions may no longer be load-bearing (model update or improved retrieval resolved the gap). Remove or shorten the Clarification, run a new experiment, compare. There is no automated probe for this — a full experiment run is required.

In both cases the test is the same: remove → run → compare to baseline → keep if scores hold, restore if they drop.

---

## Use case 3 — Retrieval parameter tuning

The agent calls Vertex AI Search with `max_results` (documents) × `max_extractive_segment_count` (segments per document). The production default (3 × 3) was set empirically. Higher values improve recall but increase latency and the token volume the model processes.

**How to find the minimum viable params:** use `shmoo` to sweep segment count for each STOPGAP scenario and find the threshold where its text first appears:

```bash
cd backend
uv run python -m scripts.vertex_ai_search shmoo \
  "<representative query>" \
  --target "<verbatim phrase from STOPGAP>" \
  --max-segment-sweep 10
```

Run this for each STOPGAP scenario. ORS 90.425 (2/4 at production params) may need more segments, not fewer — the shmoo sweep will show the crossover point. Only reduce params in scenarios where target text appears at segment counts below the current default.

---

## Running a new experiment

```bash
cd backend
uv run run-langsmith-evaluation \
  --dataset tenant-legal-qa-scenarios \
  --experiment <descriptive-name> \
  --num-repetitions 10
```

Then use `/analyze-experiment <new-experiment>` to verify no regressions. A successful optimization holds or improves all scenario means relative to the baseline.
