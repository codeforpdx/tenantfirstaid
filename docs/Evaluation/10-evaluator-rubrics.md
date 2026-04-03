# Editing Evaluator Rubrics

> **Audience**: legal contributors and content/frontend contributors. No Python required.

Rubrics are plain markdown files that define what counts as a good answer for each evaluator. Anyone who can edit a text file can improve them.

## Where the rubrics live

```
backend/evaluate/evaluators/
  legal_correctness.md    # Is the legal information accurate?
  tone.md                 # Is the tone right?
  citation_accuracy.md    # Are citations well-formed? (disabled pending calibration)
```

Each file describes scoring guidelines: what earns a 1.0, 0.5, or 0.0. The Python code in `langsmith_evaluators.py` loads these files and passes them to the AI judge — you don't need to touch the Python.

## Editing a rubric

Open the relevant `.md` file in your editor and change the wording. The evaluator uses your updated text on the next evaluation run.

**Content/frontend contributors**: edit the file, restart `langgraph dev` if you want to test, then open a pull request.

**Legal contributors**: if you have a LangSmith Plus-tier seat, you can also edit the rubric wording in the LangSmith Playground. When you find phrasing you like, copy it back into the `.md` file — the file is the source of truth.

## What to change (and what not to)

**Safe to change:**
- The plain-language description of what earns each score
- Examples of good and bad responses
- The threshold wording (e.g., "partially correct" → "correct but missing a key nuance")

**Don't change:**
- The score values themselves (0.0 / 0.5 / 1.0) — these are fixed by the `openevals` evaluator framework
- The `<Rubric>…</Rubric>` tags if present — these are used by the prompt-pull tooling
- File names — the Python code references these by name

## Keeping bound evaluators in sync

If you update a rubric file and the project has bound evaluators configured in LangSmith (see [Bound Evaluators](06-bound-evaluators.md)), the bound evaluator prompt must be updated manually in the LangSmith UI — there's no automatic sync. Ask a backend contributor or admin to update it.

---

**Next**: [Viewing & Comparing Results](11-viewing-results.md)
