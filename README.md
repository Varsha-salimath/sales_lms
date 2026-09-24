# Sales LMS

Frappe-based learning platform with a Vue 3 SPA, Docker Compose for local and production-style runs, and optional CRT schedule import from Excel.

| Item | Value |
|------|--------|
| **Stack** | Frappe 16 · Vue 3 · MariaDB (MySQL-compatible) · Redis · Docker |
| **Default app port** | **8080** (configure via `APP_PORT`) |
| **CRT course slug** | `sales-crt` |

**Security:** Do not commit `.env`, API keys, SMTP credentials, production hostnames, or curriculum files such as **`CRT-Schedule.xlsx`**. Use `.env.example` as a template only; set all secrets locally or in your deployment secret store.

For deployment notes, see **[PRODUCTION_DEPLOY.md](PRODUCTION_DEPLOY.md)** (generic checklist — no production secrets in git).

---

## Layout

| Path | Role |
|------|------|
| `backend/` | Frappe app sources (installed as **`lms`**) |
| `frontend/` | Vue SPA (built into the backend image, served via nginx) |
| `docker-compose.yml` | Compose stack (local + production-style) |
| `.env` / `.env.example` | Environment configuration (not committed) |
| `docker/Dockerfile.backend` | Backend image |
| `docker/Dockerfile.frontend` | Frontend image (`FROM` backend) |
| `docker/entrypoint-backend.sh` | Site bootstrap + serve / worker / socketio |
| `data/CRT-Schedule.xlsx` | Optional CRT workbook — **not in git** (see `data/README.md`) |

Frappe uses `DB_TYPE=mariadb` for MySQL-protocol servers. **MariaDB 10.6+** is required for Frappe 16.

---

## Quick start (local)

```bash
cp .env.example .env
# Edit .env — set DB_PASSWORD, REDIS_PASSWORD, SMTP_*, DEFAULT_SENDER, ADMIN_PASSWORD, etc.

docker compose --env-file .env build backend
docker compose --env-file .env build frontend
docker compose --env-file .env up -d
```

| Check | Value |
|-------|--------|
| App | http://localhost:8080/lms |
| Ping | `curl http://127.0.0.1:8080/api/method/ping` |
| Desk / SPA login | Use the site admin credentials you set in `.env` (`ADMIN_PASSWORD`) — **never use example passwords in production** |
| CRT schedule | http://localhost:8080/lms/crt |
| Import | http://localhost:8080/lms/crt/import |

`COMPOSE_PROFILES=embedded-db` starts the in-compose MariaDB service (`db`). Redis runs in Compose by default.

A **fresh site has no courses** until you import the CRT Excel (if you use that workflow).

### Import the CRT schedule

After login with a role that can manage courses (e.g. System Manager / Moderator / Course Creator):

1. Open `/lms/crt/import`
2. Dry-run preview (bundled Excel or upload)
3. Import into Frappe — creates/updates course `sales-crt`, chapters, lessons, and session rows
4. Open `/lms/crt`

CLI equivalent (inside backend container):

```bash
docker compose --env-file .env exec -w /home/frappe/frappe-bench backend \
  bench --site sales.localhost execute lms.lms.sales_crt.preview_import --kwargs "{'use_bundled': 1}"

docker compose --env-file .env exec -w /home/frappe/frappe-bench backend \
  bench --site sales.localhost execute lms.lms.sales_crt.import_schedule --kwargs "{'use_bundled': 1}"
```

### Containers

| Service | Role | When |
|---------|------|------|
| `frontend` | nginx reverse proxy + static assets | always — host-published `APP_PORT` |
| `backend` | Frappe + workers + socketio | always — internal |
| `redis` | cache / queue / socketio | always — internal |
| `db` | MariaDB | only if `COMPOSE_PROFILES=embedded-db` |

**Switching from an older Postgres-based local setup:** stop the stack, remove volumes `sales_db_data` and `sales_sites`, then rebuild and `up -d`.

---

## Required env (local + prod)

See `.env.example`. Compose typically requires at least:

| Key | Purpose |
|-----|---------|
| `DB_PASSWORD` | App DB password |
| `DB_ROOT_PASSWORD` | Privileged user for `bench new-site` |
| `REDIS_PASSWORD` | Compose Redis password |
| `SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD` | Outbound email |
| `DEFAULT_SENDER` | From address for Email Account bootstrap |
| `ADMIN_PASSWORD` | Initial Frappe Administrator password (strong, unique per environment) |

Optional Redis URI overrides: `REDIS_CACHE` / `REDIS_QUEUE` / `REDIS_SOCKETIO`.

---

## Production (summary)

Use the same Compose file with production values in `.env` (external MariaDB, no embedded `db` profile, LB targeting **frontend** `:8080`, required SMTP). Details: **[PRODUCTION_DEPLOY.md](PRODUCTION_DEPLOY.md)**.

Smoke test after deploy:

```bash
curl -fsS http://127.0.0.1:8080/api/method/ping
```

---

## Troubleshooting

| Symptom | Check |
|---------|--------|
| Compose refuses to start | Missing required env keys in `.env` |
| Ping 500 | DB reachability / credentials; `docker compose logs backend` |
| Redis errors with external Redis | Frappe 16 may be incompatible with some managed Redis features — prefer Compose Redis for POC |
| Empty CRT schedule | Fresh site — run Excel import |
| Assets 404 / MIME errors | Rebuild **backend** then **frontend** |

```bash
docker compose --env-file .env logs -f backend
docker compose --env-file .env restart backend
```
