# Deployment Documentation

This documentation covers how Tenant First Aid is deployed, where it runs, how configuration and secrets are managed, how to debug issues, who has access, and how the service is monitored.

## Quick start

- **Stakeholders**: Start with [Overview for Stakeholders](01-overview.md)
- **Developers**: See [Environments](02-environments.md) for where to run code
- **Operators / SREs**: See [Infrastructure](04-infrastructure.md), [Debugging](08-debugging.md), and the runbooks

## Chapters

1. **[Overview for Stakeholders](01-overview.md)** — High-level explanation of how deployments work
2. **[Environments](02-environments.md)** — Production, staging, local, and evaluation environments
3. **[Deployment Principles](03-principles.md)** — Core principles and external artifact lifecycle
4. **[Infrastructure](04-infrastructure.md)** — Digital Ocean, Nginx, Gunicorn, TLS
5. **[CI/CD Pipeline](05-cicd-pipeline.md)** — GitHub Actions workflows and automated deployment
6. **[Secrets & Configuration](06-secrets-configuration.md)** — Environment variables and credential management
7. **[Server Configuration](07-server-configuration.md)** — Nginx and systemd configuration files
8. **[Debugging & Runbooks](08-debugging.md)** — Troubleshooting procedures and incident response
9. **[Permissions](09-permissions.md)** — Access control and how to request access
10. **[Observability](10-observability.md)** — Metrics, logging, and monitoring

## Related documentation

- **[Architecture.md](../Architecture/README.md)** — Code organization and system design
- **[EVALUATION.md](../Evaluation/README.md)** — Automated quality testing with LangSmith
- **[README.md](../../README.md)** — Local development setup
