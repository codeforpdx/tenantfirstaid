# Server Configuration

The [`config/`](../../config/) directory contains reference copies of the two server configuration files:

| File | Deployed to | Managed by |
|------|-------------|------------|
| [`config/tenantfirstaid.conf`](../../config/tenantfirstaid.conf) | `/etc/nginx/sites-available/tenantfirstaid` | Manual — server admin |
| [`config/tenantfirstaid-backend.service`](../../config/tenantfirstaid-backend.service) | `/etc/systemd/system/tenantfirstaid-backend.service` | Manual — server admin |

> **These files are not auto-deployed.** The CI pipeline only deploys application code. If you change a config file in this repository, a server admin must manually copy it to the server and reload the relevant service.

## Manual server configuration changes

For Nginx config changes:

```bash
sudo cp /path/to/tenantfirstaid.conf /etc/nginx/sites-available/tenantfirstaid
sudo nginx -t               # Validate config before reloading.
sudo systemctl reload nginx
```

For systemd service changes:

```bash
sudo cp /path/to/tenantfirstaid-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart tenantfirstaid-backend
```

---

**Next**: [Debugging & Runbooks](08-debugging.md)
