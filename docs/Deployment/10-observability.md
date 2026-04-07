# Observability

## DataDog (current)

The production Gunicorn service is instrumented with DataDog for log collection and correlation. The following variables are set in the systemd service unit ([`config/tenantfirstaid-backend.service`](../../config/tenantfirstaid-backend.service)):

| Variable | Value | Purpose |
|----------|-------|---------|
| `DD_SERVICE` | `tenant-first-aid` | Service identifier in DataDog |
| `DD_ENV` | `prod` | Environment tag |
| `DD_LOGS_INJECTION` | `true` | Injects trace IDs into log lines |
| `DD_LOGS_ENABLED` | `true` | Enables log forwarding to DataDog |

The DataDog agent and its API key are configured directly on the server by a server admin and are not stored in this repository or the CI pipeline.

## LangSmith (LLM traces — development / CI only)

[LangSmith](https://smith.langchain.com/) can optionally trace LLM calls for debugging and evaluation when a `LANGSMITH_API_KEY` is set. See `backend/.env.example` for the relevant variables. LangSmith tracing is **not** enabled in the production deployment.

For running evaluations, see [`backend/evaluate/EVALUATION.md`](../Evaluation/README.md).

## Future plans

See issues tagged [`observability`](https://github.com/codeforpdx/tenantfirstaid/labels/observability) for planned monitoring improvements.

---

## Related documentation

- [Architecture.md](../Architecture/README.md) — code organization and system design
- [README.md](../../README.md) — local development setup
- [`config/`](../../config/) — server configuration files (Nginx, systemd)
- [`.github/workflows/deploy.production.yml`](../../.github/workflows/deploy.production.yml) — production CI/CD workflow
- [`.github/workflows/deploy.staging.yml`](../../.github/workflows/deploy.staging.yml) — staging CI/CD workflow
- [`backend/evaluate/EVALUATION.md`](../Evaluation/README.md) — LLM evaluation with LangSmith
