# Environments

## Deployment environments

| Environment | URL | Deployment trigger | Purpose |
|-------------|-----|--------------------|---------|
| **Production** | [tenantfirstaid.com](https://tenantfirstaid.com) | Automatic on push to `main` | Live site for end users |
| **Staging** | Internal URL (see GitHub environment settings) | Manual (`workflow_dispatch`) | Pre-production validation |
| **Local** | `http://localhost:5173` | Manual (`uv run python -m tenantfirstaid.app` + `npm run dev`) | Developer iteration and testing |

Additionally, the agent can be run locally or deployed to LangSmith Cloud for evaluation and interactive testing:

| Environment | URL | Deployment trigger | Purpose |
|-------------|-----|--------------------|---------|
| **LangGraph dev** | `http://localhost:2024` | Manual (`langgraph dev` in `backend/`) | Local Studio testing with full agent (tools, RAG). No LangSmith account required |
| **LangSmith Cloud** | LangSmith dashboard | Git push (auto-deploy) | Browser-based evaluation and Studio for Plus-tier seat holders |

The `langgraph.json` manifest in `backend/` configures both. See [`backend/evaluate/EVALUATION.md`](../Evaluation/README.md) for setup instructions.

## Environment configuration

Both production and staging have independent sets of secrets and variables managed in GitHub Actions [environment settings](https://github.com/codeforpdx/tenantfirstaid/settings/environments). This means staging can be pointed at a different server or datastore without affecting production.

For local development setup, see the [Quick Start in README.md](../../README.md#quick-start). The local environment reads credentials from `backend/.env` (git-ignored) and connects to the same Google Cloud services as production by default, using developer-scoped GCP credentials.

Notable staging-only setting: `SHOW_MODEL_THINKING` can be toggled on to surface the model's internal reasoning steps for debugging purposes.

---

**Next**: [Deployment Principles](03-principles.md)
