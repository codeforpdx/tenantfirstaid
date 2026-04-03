# Infrastructure

The application runs on a single Digital Ocean Droplet:

| Property | Value |
|----------|-------|
| Provider | [Digital Ocean](https://www.digitalocean.com/) |
| OS | Ubuntu LTS 24.04 |
| CPUs | 2 |
| RAM | 2 GB |
| Domain registrar / DNS | [Porkbun](https://porkbun.com/) — `tenantfirstaid.com` |
| TLS certificates | [Let's Encrypt](https://letsencrypt.org/) via Certbot (auto-renewing) |

## Infrastructure diagram

```mermaid
graph TB
    subgraph "Internet"
        Users["🏠 Users"]
        Certbot["Let's Encrypt<br/>(TLS certs — auto-renews)"]
        Porkbun["Porkbun DNS<br/>(tenantfirstaid.com)"]
    end

    subgraph "Digital Ocean Droplet · Ubuntu 24.04 LTS"
        Nginx["Nginx<br/>Reverse proxy + TLS<br/>Ports 443 / 80"]
        Systemd["Systemd<br/>Process manager"]
        Gunicorn["Gunicorn WSGI<br/>10 workers · Unix socket"]
        Flask["Flask Application"]
        Config["/etc/tenantfirstaid/<br/>env + credentials"]
    end

    subgraph "Google Cloud Platform"
        Gemini["Gemini 2.5 Pro<br/>(LLM)"]
        VertexRAG["Vertex AI RAG<br/>(document retrieval)"]
    end

    Users -->|HTTPS| Porkbun
    Porkbun -->|"resolves to droplet IP"| Nginx
    Certbot -.->|"renews certs"| Nginx
    Nginx -->|"static files from disk"| Users
    Nginx -->|"/api/ → Unix socket"| Gunicorn
    Systemd -->|"manages"| Gunicorn
    Gunicorn --> Flask
    Flask -->|"service account auth"| Gemini
    Gemini --> VertexRAG
    Config -.->|"env vars at startup"| Gunicorn
```

## Nginx

Nginx (config: [`config/tenantfirstaid.conf`](../../config/tenantfirstaid.conf)) does two things:

1. **Serves static files**: the built React frontend (`frontend/dist/`) is served directly from disk, with a fallback to `index.html` for client-side routing.
2. **Proxies API requests**: requests to `/api/` are forwarded to Gunicorn via a Unix domain socket (no TCP overhead).

All HTTP traffic is redirected to HTTPS. TLS is managed by Certbot.

## Gunicorn + systemd

The Flask backend runs under Gunicorn with 10 worker processes and a 300-second timeout (config: [`config/tenantfirstaid-backend.service`](../../config/tenantfirstaid-backend.service)). Systemd restarts the process on failure and ensures it starts on server reboot.

---

**Next**: [CI/CD Pipeline](05-cicd-pipeline.md)
