# Running Evaluations (CLI)

> **Audience**: backend contributors. Commands below assume you are in the `backend/` directory.
>
> To run an experiment from the browser without a terminal, see [Bound Evaluators](06-bound-evaluators.md).

```bash
cd backend/evaluate

# Run evaluation on the full dataset.
uv run run_langsmith_evaluation.py

# Run with a custom experiment label (useful for comparing before/after a change).
uv run run_langsmith_evaluation.py \
  --dataset "tenant-legal-qa-scenarios" \
  --experiment "my-experiment" \
  --num-repetitions 1

# Run multiple repetitions to measure scoring variance.
uv run run_langsmith_evaluation.py --num-repetitions 3

# Speed up slow runs by parallelising example execution.
uv run run_langsmith_evaluation.py --max-concurrency 3
```

Results appear in the LangSmith dashboard under your dataset's **Experiments** tab.

## CI/CD note

PRs from forked repos don't have access to repository secrets (including `LANGSMITH_API_KEY`), so evaluations can't run automatically in CI. Run evaluations locally before submitting a pull request for any change that might affect response quality.

---

**Next**: [Understanding Scores](15-understanding-scores.md)
