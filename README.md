# Sales LMS (CRT)

Infinity Learn **Sales LMS** — Frappe LMS for Sales Classroom Readiness Training (CRT). Infinity Learn branded Vue SPA. Curriculum comes from the CRT Excel import, not from frontend constants.

| Item | Value |
|------|--------|
| **Stack** | Frappe 16 · Vue 3 · **PostgreSQL** · Redis · Docker |
| **Local / prod app port** | **8080** (same everywhere) |
| **CRT course slug** | `sales-crt` |

**Never commit** `.env` or secrets. Copy from `.env.example` only.

For a full from-scratch production runbook, see **[PRODUCTION_DEPLOY.md](PRODUCTION_DEPLOY.md)**.

---

## Layout

| Path | Role |
|------|------|
| `backend/` | Frappe app sources (installed as **`lms`**) |
| `frontend/` | Vue SPA (Sales / Infinity Learn branded; built into the backend image, served via nginx) |
| `docker-compose.yml` | **Only** Compose file (local + prod) |
| `.env` / `.env.example` | **Only** env file |
| `docker/Dockerfile.backend` | Backend image |
| `docker/Dockerfile.frontend` | Frontend image (`FROM` backend) |
| `docker/entrypoint-backend.sh` | Site bootstrap + serve / worker / socketio |
| `data/CRT-Schedule.xlsx` | CRT curriculum workbook (import this; not auto-loaded on boot) |

No parallel compose stacks. No MariaDB/MySQL. No Redis Cloud as default.

---

## Quick start (local)

```bash
cp .env.example .env
# Edit .env — set DB_PASSWORD and required SMTP_* values

docker compose --env-file .env build backend
docker compose --env-file .env build frontend
docker compose --env-file .env up -d
```

| Check | Value |
|-------|--------|
| App | http://localhost:8080/lms |
| Ping | `curl http://127.0.0.1:8080/api/method/ping` |
| Login | `Administrator` / `ADMIN_PASSWORD` (default `admin`) |
| CRT schedule | http://localhost:8080/lms/crt |
| Import | http://localhost:8080/lms/crt/import |

`COMPOSE_PROFILES=embedded-db` starts the in-compose Postgres service (`db`). Redis always runs in Compose (known-good path for Frappe 16).

A **fresh site has no courses** until you import the Excel.

### Import the CRT schedule

After login as Administrator / Moderator / Course Creator:

1. Open `/lms/crt/import`
2. **Dry-run preview** (bundled Excel or upload)
3. **Import into Frappe** — creates/updates course `sales-crt`, Day chapters, lessons, and `Sales CRT Session` rows
4. Open `/lms/crt` — schedule is read from the backend

CLI equivalent (inside backend):

```bash
docker compose --env-file .env exec -w /home/frappe/frappe-bench backend \
  bench --site sales.localhost execute lms.lms.sales_crt.preview_import --kwargs "{'use_bundled': 1}"

docker compose --env-file .env exec -w /home/frappe/frappe-bench backend \
  bench --site sales.localhost execute lms.lms.sales_crt.import_schedule --kwargs "{'use_bundled': 1}"
```

### Containers

| Service | Role | When |
|---------|------|------|
| `frontend` | nginx reverse proxy + static assets | always — **only** host-published port (`APP_PORT`) |
| `backend` | Frappe + workers + socketio | always — internal |
| `redis` | cache / queue / socketio | always — internal |
| `db` | Postgres 16 | only if `COMPOSE_PROFILES=embedded-db` |

---

## Required env (local + prod)

Same keys in `.env.example`. Compose **will not start** without:

| Key | Purpose |
|-----|---------|
| `DB_PASSWORD` | App DB password |
| `DB_ROOT_PASSWORD` | Privileged user for `bench new-site` |
| `REDIS_PASSWORD` | Compose Redis password |
| `SMTP_HOST` | SMTP server |
| `SMTP_USER` | SMTP login |
| `SMTP_PASSWORD` | SMTP password |
| `DEFAULT_SENDER` | From address (Email Account) |

Optional Redis URI overrides: `REDIS_CACHE` / `REDIS_QUEUE` / `REDIS_SOCKETIO`.  
Otherwise URIs are built as `redis://[REDIS_USERNAME]:REDIS_PASSWORD@REDIS_HOST:REDIS_PORT?protocol=3`  
(local: empty username + Compose Redis).

---

## Production anti-footguns

1. **PostgreSQL only.** Site name **must not** equal DB name (`sales.localhost` ≠ `salesapp`).
2. **`DB_ROOT_USERNAME` must not** equal the app DB user (`salesapp`). Root creates databases; app user is runtime.
3. Never half-create a site then point it at a different DB without cleaning `site_config` + empty DB. **Ask before any wipe.**
4. **Redis:** Frappe 16 is incompatible with Redis Cloud CLIENT TRACKING (`syntax error`). Default: Compose Redis (`REDIS_HOST=redis`, `6379`).
5. Public LB/proxy must target the **frontend** container `APP_PORT` (**8080**), not uvicorn.
6. **SMTP is required** from day one.
7. Image deploy does **not** create CRT content. Import Excel after boot.
8. **Same `APP_PORT` for local and prod (8080).**

---

## Production (DevOps)

Same Compose file and env keys — only values change.

1. Clear `COMPOSE_PROFILES` (do **not** start embedded Postgres).
2. Set Cloud SQL:
   - `DB_HOST` = private IP
   - `DB_NAME` / `DB_USER` = **`salesapp`** (site hostname ≠ DB name)
   - `DB_PASSWORD`, `DB_ROOT_USERNAME`, `DB_ROOT_PASSWORD` (root must be able to create DB on first boot; root ≠ salesapp)
3. Keep **Compose Redis** unless an external Redis is proven with Frappe 16.
4. Set **required** SMTP, `APP_PORT=8080`, site host, LB real-IP.
5. Build and run:

```bash
docker compose --env-file .env build backend
docker compose --env-file .env build frontend
docker compose --env-file .env up -d
```

Smoke: `curl -fsS http://127.0.0.1:8080/api/method/ping` → `pong`

Then import CRT Excel (content is not in the image).

---

## SMTP

`SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, and `DEFAULT_SENDER` are **required**. On site create/migrate the entrypoint bootstraps the Desk outgoing Email Account from these values.

---

## Troubleshooting

| Symptom | Check |
|---------|--------|
| Compose refuses to start | Missing `DB_PASSWORD` / `REDIS_PASSWORD` / required `SMTP_*` / `DEFAULT_SENDER` |
| Ping 500 | Postgres reachability / credentials; `docker compose logs backend` |
| Redis `syntax error` | You pointed Frappe 16 at Redis Cloud CLIENT TRACKING — switch to Compose Redis |
| Public domain returns foreign JSON auth errors | LB is not targeting Compose frontend `:8080` |
| Empty CRT schedule | Expected on a fresh site — run Excel import |
| Assets 404 / MIME errors | Rebuild **backend** then **frontend** so LMS asset symlink is baked in |

```bash
docker compose --env-file .env logs -f backend
docker compose --env-file .env restart backend
```
