# Server configuration

This directory contains reference copies of the server configuration files for the Digital Ocean droplet (Ubuntu LTS 24.04, 2 CPUs, 2 GB RAM). See [Deployment.md](../Deployment.md) for full infrastructure details.

> **These files are not auto-deployed.** The CI/CD pipeline only deploys application code. If you change a file here, a server admin must manually copy it to the server and reload the relevant service.

## File paths on the server

| File in this repo | Path on server | Reload command |
|---|---|---|
| `tenantfirstaid.conf` | `/etc/nginx/sites-available/tenantfirstaid` | `sudo nginx -t && sudo systemctl reload nginx` |
| `tenantfirstaid-backend.service` | `/etc/systemd/system/tenantfirstaid-backend.service` | `sudo systemctl daemon-reload && sudo systemctl restart tenantfirstaid-backend` |
