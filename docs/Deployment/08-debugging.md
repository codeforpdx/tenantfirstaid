# Debugging & Runbooks

## Accessing the droplet

Server admins access the droplet via the **Digital Ocean web console** — no local SSH setup required:

1. Log in to the [Digital Ocean control panel](https://cloud.digitalocean.com/).
2. Navigate to **Droplets** and select the `tenantfirstaid` droplet.
3. Click **Console** (top right of the droplet detail page) to open a browser-based terminal session.

If you need server access for the first time, see [Permissions](09-permissions.md) to request a Digital Ocean team invite.

## Using observability to narrow down the issue

Before running commands on the server, use available signals to identify the affected layer:

1. **Check the GitHub Actions deploy log first.** Open the [Actions tab](https://github.com/codeforpdx/tenantfirstaid/actions) and look at the most recent deploy run. A failed step there means the issue is in the deploy pipeline, not the running application.

2. **Check DataDog** (if you have access). The production backend ships structured logs with trace injection enabled (`DD_LOGS_INJECTION=true`). Filter by `service:tenant-first-aid` and `env:prod`. Look for:
   - HTTP 5xx errors → likely Gunicorn / Flask issue
   - Timeout patterns → check Gunicorn worker count or GCP API latency
   - Crash loops (repeated startup logs) → missing or malformed env vars

3. **Check the Nginx access log** for HTTP status codes if the DataDog agent is not forwarding logs (see [View logs](#view-logs) below). A 502 means Gunicorn is not running; a 504 means it is running but timing out.

4. **Check application logs via journalctl** (requires droplet console access) to see Python tracebacks and startup errors.

Once you have a hypothesis, use the commands in the sections below to confirm and fix it.

## Useful commands

### Check service status

```bash
sudo systemctl status tenantfirstaid-backend
```

### View logs

```bash
# Live-tail application logs.
sudo journalctl -u tenantfirstaid-backend -f

# Last 200 lines.
sudo journalctl -u tenantfirstaid-backend -n 200

# Nginx access and error logs.
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Restart services

```bash
sudo systemctl restart tenantfirstaid-backend
sudo systemctl reload nginx
```

### Inspect the deployed environment file

```bash
sudo cat /etc/tenantfirstaid/env
```

### Check a failed deploy

Open the [GitHub Actions tab](https://github.com/codeforpdx/tenantfirstaid/actions) and select the failing workflow run. Each step's output is visible in the run log.

## SRE Runbooks

Each runbook follows **Detect → Diagnose → Resolve → Notify** steps.

> **Discord**: post all incident notifications and resolution confirmations in `#tenantfirstaid-general` on the [Code for PDX Discord](https://discord.gg/codeforpdx).

### Runbook: Site down / 502 Bad Gateway

**Symptoms**: users see a 502 error; Nginx access log shows `502` responses on `/api/` routes.

**Detect**:
- Check [tenantfirstaid.com](https://tenantfirstaid.com) — if the frontend loads but the chatbot fails, the backend is down.
- Check the most recent GitHub Actions deploy run for errors.

**Diagnose**:
```bash
sudo systemctl status tenantfirstaid-backend
sudo journalctl -u tenantfirstaid-backend -n 50
```
Look for: crash on startup (missing env var), OOM kill, or permission error on the socket.

**Resolve**:
```bash
# Restart the backend service.
sudo systemctl restart tenantfirstaid-backend
sudo systemctl status tenantfirstaid-backend   # Confirm it is active (running).
```
If it won't start, check `/etc/tenantfirstaid/env` for missing or malformed variables. Trigger a fresh deploy to rewrite the env file if needed.

**Notify**: Post in `#tenantfirstaid-general`:
> ⚠️ **Incident**: backend down (502). Restarted tenantfirstaid-backend at [time]. Monitoring for stability. Root cause: [brief description].

### Runbook: Gemini API errors

**Symptoms**: chatbot returns an error message or hangs; journalctl shows `google.api_core.exceptions` tracebacks.

**Common error classes**:

| Error | Likely cause | Action |
|-------|-------------|--------|
| `ResourceExhausted` / 429 | Quota exceeded | Wait for quota reset (check [GCP console quotas](https://console.cloud.google.com/iam-admin/quotas)); request quota increase if recurring |
| `PermissionDenied` / 403 | Service account lacks Vertex AI role, or credentials file is stale | Re-deploy (rewrites credentials file); verify service account roles in GCP IAM |
| `Unauthenticated` / 401 | Service account key expired or malformed | Re-deploy; if still failing, rotate the `GOOGLE_SERVICE_ACCOUNT_CREDENTIALS` secret and re-deploy |
| `ServiceUnavailable` / 503 | GCP regional outage | Check [Google Cloud Status](https://status.cloud.google.com/); no action until outage clears |
| `InvalidArgument` / 400 | Model name changed or unsupported | Check `MODEL_NAME` variable in GitHub environment settings against the [Gemini model list](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/models) |

**Diagnose**:
```bash
sudo journalctl -u tenantfirstaid-backend -n 100 | grep -i "exception\|error\|google"
sudo cat /etc/tenantfirstaid/env | grep -E "MODEL_NAME|GOOGLE_CLOUD|VERTEX"
```

**Resolve**: apply the action from the table above. For quota issues, consider temporarily disabling the chatbot route in Nginx while waiting.

**Notify**: Post in `#tenantfirstaid-general`:
> ⚠️ **Incident**: Gemini API errors ([error class]). Status: [investigating / resolved]. Impact: chatbot unavailable / degraded. ETA: [if known].

### Runbook: Vertex AI RAG errors

**Symptoms**: chatbot responds without legal citations, or journalctl shows `VertexAI` / `datastore` errors.

**Diagnose**:
```bash
sudo journalctl -u tenantfirstaid-backend -n 100 | grep -i "retriev\|datastore\|rag\|vertex"
sudo cat /etc/tenantfirstaid/env | grep VERTEX_AI_DATASTORE
```
Verify the corpus ID in the env file matches an existing corpus in [GCP Vertex AI Search](https://console.cloud.google.com/gen-app-builder/data-stores).

**Common causes**:

| Symptom | Cause | Fix |
|---------|-------|-----|
| `NOT_FOUND` on datastore ID | Corpus deleted or wrong ID | Update `VERTEX_AI_DATASTORE` in GitHub environment settings and redeploy |
| Empty retrieval results | Corpus not indexed / wrong metadata filters | Re-ingest documents via `backend/scripts/create_vector_store.py`; follow [External artifact lifecycle](03-principles.md#external-artifact-lifecycle) |
| Auth errors on RAG calls | Same as Gemini auth issues | See Gemini runbook above |

**Resolve**: update the `VERTEX_AI_DATASTORE` environment variable to a valid corpus ID and trigger a redeploy.

**Notify**: Post in `#tenantfirstaid-general`:
> ⚠️ **Incident**: RAG retrieval errors — chatbot may respond without citations. Status: [investigating / resolved]. Corpus ID in use: [value from env].

### Runbook: TLS certificate expiry

**Symptoms**: browsers show a certificate error; `curl -I https://tenantfirstaid.com` returns an SSL handshake error.

**Diagnose**:
```bash
sudo certbot certificates          # Show expiry dates.
sudo systemctl status certbot.timer  # Check the auto-renewal timer is active.
sudo journalctl -u certbot -n 50   # Look for renewal errors.
```

**Resolve**:
```bash
sudo certbot renew --dry-run       # Test renewal without committing.
sudo certbot renew                 # Renew all certificates.
sudo systemctl reload nginx        # Reload Nginx to pick up new certs.
```
If the timer is disabled: `sudo systemctl enable --now certbot.timer`.

**Notify**: Post in `#tenantfirstaid-general`:
> ⚠️ **Incident**: TLS certificate expired / near expiry. Renewed at [time]. Next expiry: [date from certbot certificates].

### Runbook: Failed deployment

**Symptoms**: GitHub Actions deploy run shows a red ✗; the site may be on an older version or partially broken.

**Detect**: check the [Actions tab](https://github.com/codeforpdx/tenantfirstaid/actions) for the failing run and identify the failing step.

**Common failure points**:

| Failing step | Likely cause | Fix |
|-------------|-------------|-----|
| **Build UI** | npm dependency or build error | Fix in code; re-merge or trigger `workflow_dispatch` |
| **Upload via SCP** | Droplet unreachable or SSH key invalid | Check droplet status in Digital Ocean console; verify `SSH_KEY` secret is current |
| **uv sync** | Lockfile conflict or network error | Re-run the workflow; if persistent, check `uv.lock` in the repo |
| **Write env file** | Malformed secret value (newline in secret) | Edit the offending secret in GitHub environment settings |
| **systemctl restart** | Service unit file missing or broken | Manually apply `config/tenantfirstaid-backend.service` to the server |

**Resolve**: fix the root cause and re-trigger the deploy (push a fix commit, or use `workflow_dispatch` on the staging workflow).

**Notify**: Post in `#tenantfirstaid-general`:
> ⚠️ **Incident**: deploy failed at step "[step name]" — production may be on previous version. Fix in progress. PR/commit: [link].

## Common issues

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| 502 Bad Gateway | Gunicorn not running | See [Runbook: Site down / 502](#runbook-site-down--502-bad-gateway) |
| App starts then crashes | Missing or invalid env var | Check `/etc/tenantfirstaid/env`; look for the specific error in `journalctl` |
| GCP API errors | Bad or expired service account credentials | Re-deploy (the workflow rewrites the credentials file) |
| TLS certificate expiry | Certbot renewal failed | See [Runbook: TLS certificate expiry](#runbook-tls-certificate-expiry) |
| Deploy stuck / hanging | Previous deploy still running | Cancel it in the GitHub Actions UI; the concurrency group will allow the next one to proceed |
| Chatbot returns wrong answers | Stale or incorrect RAG corpus | Check `VERTEX_AI_DATASTORE` in the env file; see [External artifact lifecycle](03-principles.md#external-artifact-lifecycle) |

---

**Next**: [Permissions](09-permissions.md)
