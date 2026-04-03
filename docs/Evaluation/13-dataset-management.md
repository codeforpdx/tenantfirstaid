# Dataset Management (CLI)

> **Audience**: backend contributors. Commands below assume you are in the `backend/` directory.
>
> - To add or edit examples in the browser without a terminal, see [Adding Examples in the Browser](05-examples-in-browser.md).
> - To add examples locally without Python knowledge, see [Contributing Test Examples](08-contributing-examples.md).

All dataset CLI operations go through `langsmith_dataset.py`.

## Initial push (first-time or after local edits)

```bash
uv run python -m evaluate.langsmith_dataset dataset push \
  evaluate/dataset-tenant-legal-qa-examples.jsonl \
  tenant-legal-qa-scenarios
```

Creates the dataset in LangSmith if it doesn't exist, then uploads all examples.

## Pull after editing in the browser

```bash
uv run python -m evaluate.langsmith_dataset dataset pull \
  tenant-legal-qa-scenarios \
  evaluate/dataset-tenant-legal-qa-examples.jsonl
```

Overwrites the local file with whatever is currently in LangSmith. Commit the result.

## Validate the local file

```bash
uv run python -m evaluate.langsmith_dataset dataset validate \
  evaluate/dataset-tenant-legal-qa-examples.jsonl
```

Checks every line against the schema before pushing, catching formatting mistakes early.

## Check for content drift between local and remote

```bash
uv run python -m evaluate.langsmith_dataset dataset diff \
  evaluate/dataset-tenant-legal-qa-examples.jsonl \
  tenant-legal-qa-scenarios
```

Reports three categories:

| Symbol | Meaning |
|--------|---------|
| `<` | example exists only locally (would be lost on a pull, missing on a push) |
| `>` | example exists only in LangSmith |
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

`dataset diff` is the right first step before pushing or pulling.

## Assigning `scenario_id` to UI-created examples

Examples added via the LangSmith browser UI won't have a `scenario_id`. The tooling uses `scenario_id` as the stable key for diff, merge, and push, so you must assign one before committing.

1. **Pull** to get the current state:

   ```bash
   uv run python -m evaluate.langsmith_dataset dataset pull \
     tenant-legal-qa-scenarios \
     evaluate/dataset-tenant-legal-qa-examples.jsonl
   ```

2. **Identify** new examples — they'll have `"metadata": null` or no `scenario_id` field.

3. **Assign** the next available integer (one higher than the current maximum), plus the other required metadata fields:

   ```json
   {
     "metadata": { "scenario_id": 42, "city": null, "state": "OR",
                   "tags": ["city-None", "state-OR"], "dataset_split": ["train"] },
     "inputs": { "query": "...", "city": null, "state": "OR" },
     "outputs": { "facts": [...], "reference_conversation": [...] }
   }
   ```

4. **Validate**, **push**, and **commit**:

   ```bash
   uv run python -m evaluate.langsmith_dataset dataset validate \
     evaluate/dataset-tenant-legal-qa-examples.jsonl

   uv run python -m evaluate.langsmith_dataset dataset push \
     evaluate/dataset-tenant-legal-qa-examples.jsonl \
     tenant-legal-qa-scenarios

   git add evaluate/dataset-tenant-legal-qa-examples.jsonl
   git commit -m "add scenario_id to UI-created examples"
   ```

## Fine-grained example operations

```bash
# List all examples (scenario_id, tags, first 80 chars of the question)
uv run python -m evaluate.langsmith_dataset example list tenant-legal-qa-scenarios

# Append new examples from a JSONL file without touching existing ones
uv run python -m evaluate.langsmith_dataset example append \
  tenant-legal-qa-scenarios path/to/new-examples.jsonl

# Remove an example by its scenario_id
uv run python -m evaluate.langsmith_dataset example remove \
  tenant-legal-qa-scenarios 42
```

---

**Next**: [Running Evaluations (CLI)](14-running-evaluations.md)
