# Server Configuration Reference

This directory holds reference copies of the server configuration files for the Digital Ocean droplet. Full infrastructure details are in [Deployment.md](../Deployment.md).

> **These files are not auto-deployed.** The CI/CD pipeline only deploys application code. If you change a file here, a server admin must manually copy it to the server and reload the affected service.

## Configuration files

| File | Deployed to | Reload command |
|------|-------------|----------------|
| `tenantfirstaid.conf` | `/etc/nginx/sites-available/tenantfirstaid` | `sudo nginx -t && sudo systemctl reload nginx` |
| `tenantfirstaid-backend.service` | `/etc/systemd/system/tenantfirstaid-backend.service` | `sudo systemctl daemon-reload && sudo systemctl restart tenantfirstaid-backend` |

See [Deployment.md — Manual server configuration changes](../Deployment.md#manual-server-configuration-changes) for step-by-step instructions.
