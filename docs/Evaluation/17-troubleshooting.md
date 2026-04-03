# Troubleshooting

## "Dataset not found"

The dataset hasn't been pushed yet. Run:

```bash
uv run python -m evaluate.langsmith_dataset dataset push \
  evaluate/dataset-tenant-legal-qa-examples.jsonl \
  tenant-legal-qa-scenarios
```

## Scores seem wrong or inconsistent

LLM-as-judge has its own biases and can be inconsistent on borderline cases. Review the judge's written rationale for specific failing examples in the LangSmith UI, then refine the evaluator rubrics in `evaluators/*.md` if the scoring logic is the problem. See [Editing Evaluator Rubrics](10-evaluator-rubrics.md).

## Evaluation is too slow

Pass `--max-concurrency 3` (or higher) to run multiple examples in parallel:

```bash
uv run run_langsmith_evaluation.py --max-concurrency 3
```

Alternatively, reduce the dataset size in LangSmith temporarily to evaluate a representative subset.

## `langgraph dev` won't start

- Check that `backend/.env` exists and has all required variables — especially `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_CLOUD_PROJECT`, and `VERTEX_AI_DATASTORE`.
- Check that the credentials file exists at the path specified in `GOOGLE_APPLICATION_CREDENTIALS`.
- Run `uv sync` to ensure dependencies are up to date.

## Agent returns no citations / empty RAG results

- Check `VERTEX_AI_DATASTORE` in `.env` — it may point to a deleted or renamed corpus.
- Verify the corpus still exists in [GCP Vertex AI Search](https://console.cloud.google.com/gen-app-builder/data-stores).
- Ask a backend contributor to check the deployment's environment variables.

---

**Next**: [Roadmap](18-roadmap.md)
