# Automated Evaluation with LangSmith

> **This document has moved.** The evaluation documentation is now the **Evaluation
> Guide**, built with [Great Docs](https://posit-dev.github.io/great-docs/) alongside
> the rest of the backend docs. The narrative source lives in
> [`backend/evaluation_guide/`](../evaluation_guide/index.qmd). Build the site with
> `mise run docs` from `backend/`, then open `backend/great-docs/_site/index.html` and
> pick **Evaluation Guide** from the navbar.

The guide is split into short, audience-oriented chapters. Start with
[Overview](../evaluation_guide/getting-started/overview.qmd) and
[Definitions](../evaluation_guide/getting-started/definitions.qmd), then follow
the reading path for your role from the
[guide index](../evaluation_guide/index.qmd):

- **Legal / content contributor (browser only)** — Cloud Studio, editing the system
  prompt and rubrics, adding examples in the browser, and running experiments from the
  UI.
- **Frontend / content contributor (terminal, not Python-deep)** — local Studio with
  `langgraph dev`, editing prompts and rubrics locally, contributing test examples.
- **Backend contributor** — setup and environment, the dataset CLI, running
  evaluations, understanding scores and variance, workflows, and troubleshooting.

> 💡 Using Claude Code? Type `/evaluation` in the Claude Code UI for guided
> evaluation-workflow assistance.
