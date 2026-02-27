# Server configuration

This directory contains reference copies of the server configuration files. For full deployment documentation, see [Deployment.md](../Deployment.md).

> These files are **not auto-deployed** by the CI pipeline. Changes must be manually copied to the server by a server admin. See [Deployment.md — Manual server configuration changes](../Deployment.md#manual-server-configuration-changes).

## Files and their deployed paths

| File | Deployed path |
|------|--------------|
| `tenantfirstaid-backend.service` | `/etc/systemd/system/tenantfirstaid-backend.service` |
| `tenantfirstaid.conf` | `/etc/nginx/sites-available/tenantfirstaid` |
