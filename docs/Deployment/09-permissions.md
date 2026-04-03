# Permissions

## Current access levels

| Role | Access |
|------|--------|
| **Server admin** | Digital Ocean team membership (web console access to the droplet); can restart services, view logs, edit config files, and manage GitHub Actions environment secrets |
| **GitHub maintainer** | Can trigger manual (staging) deploys and read the deploy workflow output; cannot view GitHub Actions secrets |
| **Contributor** | No direct server access; contributes via pull requests which deploy automatically on merge |

## How to request access

Access is managed through [Code for PDX](https://codeforpdx.org/):

1. Complete the [Code for PDX onboarding](https://www.codepdx.org/volunteer) and join the Discord server.
2. Post in `#tenantfirstaid-general` on Discord describing the access you need and why.
3. An existing admin will review the request and grant the appropriate level of access.

For Google Cloud (Vertex AI) access needed for local development, see [README.md](../../README.md#prerequisites).

---

**Next**: [Observability](10-observability.md)
