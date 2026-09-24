# Production deploy (generic)

This document is a **public-safe checklist**. Hostnames, database endpoints, SMTP accounts, and administrator passwords belong only in **private** runbooks and secret stores — never in git.

## Prerequisites

- Linux VM or host with Docker Engine + Compose v2
- External **MariaDB 10.6+** (or compatible MySQL protocol), reachable from the VM
- Outbound SMTP (TLS on port 587 is common)
- TLS termination at a load balancer or reverse proxy in front of the **frontend** container

## Environment

1. Copy `.env.example` to `.env` on the server.
2. Set `COMPOSE_PROFILES=` (empty) so embedded MariaDB is **not** started.
3. Set `APP_PORT=8080` unless your platform requires another port (LB should target frontend, not uvicorn directly).
4. Set `SITE_NAME` and `HOST_NAME` to your **public** site identity (Frappe site folder vs public URL — they may differ).
5. Set `DB_TYPE=mariadb`, `DB_HOST`, `DB_PORT=3306`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, and root/bootstrap credentials per your DBA.
6. Set `REDIS_HOST=redis` and `REDIS_PASSWORD` for in-compose Redis unless you have validated an external Redis with Frappe 16.
7. Set all `SMTP_*` variables and `DEFAULT_SENDER`.
8. Set a **strong** `ADMIN_PASSWORD` (and rotate after first login if your policy requires it).
9. If passwords contain `$`, wrap values in single quotes in `.env` so Compose does not interpret them.

## Build and run

```bash
docker compose --env-file .env build backend
docker compose --env-file .env build frontend
docker compose --env-file .env up -d
```

## Smoke tests

```bash
curl -fsS http://127.0.0.1:8080/api/method/ping
curl -fsSI http://127.0.0.1:8080/lms
```

Replace host with your public URL when testing through the load balancer.

## CRT curriculum (optional)

If you use the Sales CRT Excel workflow, place **`CRT-Schedule.xlsx`** in `data/` before building the backend image (file is not in git). Import via `/lms/crt/import` or documented bench execute commands after the site is up.

## Operations

- Logs: `docker compose --env-file .env logs -f backend`
- Restart: `docker compose --env-file .env restart backend`
- Never commit `.env` or paste production credentials into issues or public repos.

For organization-specific infrastructure (private Git remotes, domains, RDS ARNs, SES regions), use your **internal** deployment documentation.
