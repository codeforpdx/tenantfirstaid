# Understanding Scores

> **Audience**: primarily backend contributors calibrating evaluators. Legal contributors can read score rationales directly in the LangSmith UI without needing this chapter.

Each example gets a score between 0.0 and 1.0 for each active evaluator. The overall pass rate is the average across all examples and evaluators.

## Legal Correctness

Is the legal information accurate under Oregon tenant law?

| Score | Meaning |
|-------|---------|
| 1.0 | Legally accurate |
| 0.5 | Partially correct or missing important nuance |
| 0.0 | Legally wrong or misleading |

## Tone

Is the response appropriately professional, accessible, and empathetic?

| Score | Meaning |
|-------|---------|
| 1.0 | Gets the tone right |
| 0.5 | Too formal, too casual, or inconsistent |
| 0.0 | Dismissive, condescending, or inappropriate |

**Patterns that reliably fail tone evaluation:**
- Opening with "As a legal expert..." (implies the chatbot is giving legal advice)
- Dense legal jargon without plain-language explanation
- Dismissive or condescending phrasing toward the tenant

## Evaluators under construction

These exist in the code but are disabled pending calibration: citation accuracy, citation format, completeness, tool usage, performance.

## When scores seem wrong or inconsistent

LLM-as-judge has its own biases and can be inconsistent on borderline cases. Review the judge's written rationale for specific failing examples in the LangSmith UI. If the scoring logic is the problem, refine the rubrics in `evaluators/*.md` (see [Editing Evaluator Rubrics](10-evaluator-rubrics.md)).

---

**Next**: [Typical Workflows](16-workflows.md)
