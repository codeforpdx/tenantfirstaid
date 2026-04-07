# Automated Evaluation with LangSmith

This documentation covers how to run automated quality tests on the Tenant First Aid chatbot using LangSmith, including dataset management, evaluation execution, and result interpretation.

Start with [Overview](01-overview.md) and [Definitions](02-definitions.md) — they're short and shared by all audiences. Then follow the path for your role.

---

## If you're a legal or content contributor (browser only)

No terminal needed. Requires a LangSmith Plus-tier seat and access to the Cloud deployment.

1. [Testing with Cloud Studio](04-cloud-studio.md) — chat with the agent and iterate on the system prompt in your browser
2. [Editing the System Prompt](09-system-prompt.md) — change the chatbot's tone, rules, and legal guardrails
3. [Editing Evaluator Rubrics](10-evaluator-rubrics.md) — change what counts as a good answer
4. [Adding or Editing Examples in the Browser](05-examples-in-browser.md) — add test questions and reference answers in LangSmith
5. [Running Experiments from the UI](06-bound-evaluators.md) — start a scoring run without writing code
6. [Viewing & Comparing Results](11-viewing-results.md) — read the scores and the judge's rationale

---

## If you're a frontend or content contributor (terminal-comfortable, not Python-deep)

You're comfortable with a terminal and a text editor but don't need to touch Python or LangChain internals.

1. [Local Studio with `langgraph dev`](07-local-studio.md) — spin up the full agent locally without a LangSmith account
2. [Editing the System Prompt](09-system-prompt.md) — edit `system_prompt.md` directly and see it take effect immediately
3. [Editing Evaluator Rubrics](10-evaluator-rubrics.md) — edit `evaluators/*.md` in your code editor
4. [Contributing Test Examples](08-contributing-examples.md) — add prompt-attack scenarios or edge cases without Python knowledge
5. [Viewing & Comparing Results](11-viewing-results.md) — read the scores in LangSmith

---

## If you're a backend contributor

You'll use the full dataset CLI and run evaluations programmatically.

1. [Setup & Environment Variables](12-setup-and-environment.md) — configure your local environment
2. [Dataset Management (CLI)](13-dataset-management.md) — push, pull, validate, diff
3. [Running Evaluations (CLI)](14-running-evaluations.md) — execute the full test suite
4. [Understanding Scores](15-understanding-scores.md) — calibrate evaluators and interpret results
5. [Typical Workflows](16-workflows.md) — common patterns and step-by-step guides
6. [Troubleshooting](17-troubleshooting.md) — fix things when they break

---

## All chapters

### Common ground
1. [Overview](01-overview.md) — what evaluation is and why it matters
2. [Definitions](02-definitions.md) — key concepts and terminology
3. [Data Flow](03-data-flow.md) — how data moves through the evaluation system

### Legal contributors (Cloud/browser)
4. [Cloud Studio](04-cloud-studio.md) — testing the agent via LangSmith Cloud
5. [Examples in the Browser](05-examples-in-browser.md) — adding and editing test examples in LangSmith UI
6. [Bound Evaluators](06-bound-evaluators.md) — running experiments from the LangSmith UI

### Frontend / content contributors (local dev)
7. [Local Studio](07-local-studio.md) — testing the agent with `langgraph dev`
8. [Contributing Test Examples](08-contributing-examples.md) — adding examples without Python knowledge

### Shared (legal + content contributors)
9. [System Prompt](09-system-prompt.md) — editing the chatbot's instructions
10. [Evaluator Rubrics](10-evaluator-rubrics.md) — editing scoring criteria
11. [Viewing & Comparing Results](11-viewing-results.md) — browsing experiment results in LangSmith

### Backend contributors
12. [Setup & Environment Variables](12-setup-and-environment.md) — environment configuration
13. [Dataset Management (CLI)](13-dataset-management.md) — push, pull, validate, diff
14. [Running Evaluations (CLI)](14-running-evaluations.md) — executing the evaluation suite
15. [Understanding Scores](15-understanding-scores.md) — what scores mean and how to calibrate them
16. [Typical Workflows](16-workflows.md) — common patterns
17. [Troubleshooting](17-troubleshooting.md) — common issues and solutions
18. [Roadmap](18-roadmap.md) — planned improvements

---

## Related documentation

- [Architecture](../Architecture/README.md) — code organization and system design
- [Deployment](../Deployment/README.md) — how the system is deployed and operated
