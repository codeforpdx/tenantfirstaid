# CI/CD Pipeline

```mermaid
flowchart TD
    Trigger["Push to main (production)<br/>or manual trigger (staging)"] --> Checkout["Checkout source code"]
    Checkout --> NodeSetup["Set up Node 20<br/>(cached)"]
    NodeSetup --> BuildUI["Build React frontend<br/>npm ci && npm run build"]
    BuildUI --> SCPBackend["Upload backend/ to droplet via SCP<br/>(replaces existing directory)"]
    SCPBackend --> SCPFrontend["Upload frontend/dist to droplet via SCP<br/>(appends — does not replace backend)"]
    SCPFrontend --> UVInstall["SSH: install uv on droplet<br/>(skip if already present)"]
    UVInstall --> UVSync["SSH: uv sync<br/>(install / update Python deps from lockfile)"]
    UVSync --> WriteEnv["SSH: write /etc/tenantfirstaid/env<br/>(inject GitHub secrets as env vars)"]
    WriteEnv --> WriteCreds["SSH: write /etc/tenantfirstaid/google-service-account.json<br/>(GCP service account)"]
    WriteCreds --> Restart["SSH: systemctl restart tenantfirstaid-backend<br/>+ systemctl reload nginx"]
```

## Workflow files

- **Production**: [`.github/workflows/deploy.production.yml`](../../.github/workflows/deploy.production.yml) — triggers on every push to `main`.
- **Staging**: [`.github/workflows/deploy.staging.yml`](../../.github/workflows/deploy.staging.yml) — triggered manually via `workflow_dispatch` in the GitHub Actions UI.

The two workflows are structurally identical; the only difference is which GitHub Actions environment (`production` vs `staging`) they read credentials from.

> **Nginx config and systemd service are not auto-deployed.** The files in `config/` are version-controlled here for reference, but the CI pipeline does not copy them to the server. Changes to Nginx or systemd configuration require a manual step by a server admin (see [Manual server configuration changes](07-server-configuration.md#manual-server-configuration-changes)).

---

**Next**: [Secrets & Configuration](06-secrets-configuration.md)
