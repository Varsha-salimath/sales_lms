# Sales LMS — Production deploy

| Item | Value |
|------|--------|
| Bitbucket repo | `git@bitbucket.org:CodeRepoInfinitylearn/saleslms.git` |
| Branch | `main` |
| Prod domain | `saleslms.infinitylearn.com` |
| Site name (`SITE_NAME`) | `saleslms.infinitylearn.com` |
| VM path | `<VM_PATH>` e.g. `/var/www/sales-lms/sales_lms` |
| Database (`DB_NAME` / `DB_USER`) | `salesapp` |
| MySQL host | `<DB_HOST>` (AWS POC MariaDB 10.6+ / MySQL-compatible — **not** Genius LMS Postgres on GCP) |
| App port | **8080** (LB → VM `:8080`) |
| Redis | Compose only — `REDIS_HOST=redis`, `REDIS_PORT=6379`, `REDIS_USERNAME=` empty |
| Login | `Administrator` / `ADMIN_PASSWORD` from `.env` |

**Never commit** `.env`.

Frappe uses `DB_TYPE=mariadb` for MySQL-protocol servers. **MariaDB 10.6+ is required** (Oracle MySQL 8 is not supported).

---

## Before you start

- VM: Docker Engine + Compose v2, Git access to Bitbucket, outbound MySQL `:3306` and SMTP `:587`.
- Prod `.env`: `COMPOSE_PROFILES=` (empty — no embedded MariaDB).
- `SITE_NAME` ≠ `DB_NAME` (site = domain, db = `salesapp`).
- `DB_ROOT_USERNAME` ≠ `salesapp` (use `root` or another privileged MySQL user).
- Do **not** use Redis Cloud (Frappe 16 CLIENT TRACKING breaks).
- SMTP required — compose/entrypoint fail without `SMTP_*` and `DEFAULT_SENDER`.
- Docker deploy does **not** copy local course DB state — import CRT Excel after boot.
- Before build: copy **`CRT-Schedule.xlsx`** into `data/` from your team secure share (not in git — see `data/README.md`).

Prod `.env` minimum:

```env
COMPOSE_PROFILES=
APP_PORT=8080
SITE_NAME=saleslms.infinitylearn.com
HOST_NAME=https://saleslms.infinitylearn.com
ADMIN_PASSWORD=<strong-secret>

DEVELOPER_MODE=0
LMS_ALLOW_GUEST_ACCESS=0
LMS_DISABLE_SIGNUP=1
ALLOW_DEMO_LEARNER=0

DB_TYPE=mariadb
DB_HOST=<aws-mariadb-host>
DB_PORT=3306
DB_NAME=salesapp
DB_USER=salesapp
DB_PASSWORD=<salesapp-password>
DB_ROOT_USERNAME=root
DB_ROOT_PASSWORD=<privileged-user-password>

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_USERNAME=
REDIS_PASSWORD=<redis-password>

SMTP_HOST=<smtp-host>
SMTP_PORT=587
SMTP_USER=<smtp-user>
SMTP_PASSWORD=<smtp-password>
SMTP_TLS=1
SMTP_SSL=0
DEFAULT_SENDER=donotreply@example.com
DEFAULT_SENDER_NAME=Sales LMS

UPSTREAM_REAL_IP_ADDRESS=<lb-cidr-or-ip>
UPSTREAM_REAL_IP_HEADER=X-Forwarded-For
UPSTREAM_REAL_IP_RECURSIVE=on
```

---

## Commands (run in order)

### 0. Prerequisites (on Sales VM)

```bash
nc -vz <DB_HOST> 3306
nc -vz <SMTP_HOST> 587
docker ps   # confirm no old genius/sales stacks conflicting on :8080
```

### 1. Get code

```bash
git clone git@bitbucket.org:CodeRepoInfinitylearn/saleslms.git
cd <repo-folder>    # e.g. sales_lms under <VM_PATH>
git checkout main
git pull origin main
```

### 2. Create prod `.env`

```bash
cp .env.example .env
chmod 600 .env
# Edit .env — prod values above. COMPOSE_PROFILES must be empty.
```

### 3. Build images (backend first)

```bash
docker compose --env-file .env build backend
docker compose --env-file .env build frontend
```

### 4. Start stack

```bash
docker compose --env-file .env up -d
docker compose --env-file .env ps
```

Expected containers:

| Container | Role |
|-----------|------|
| `sales_lms_frontend` | nginx — **only** host port `0.0.0.0:8080→8080` |
| `sales_lms_backend` | Frappe + worker + schedule + socketio |
| `sales_lms_redis` | Compose Redis (internal) |
| **No** `sales_lms_db` | Prod uses AWS MariaDB/MySQL-compatible DB only |

Watch bootstrap:

```bash
docker compose --env-file .env logs -f backend
```

Wait until site is created and workers are running (Ctrl+C to exit logs).

### 5. VM smoke checks (before LB cutover)

```bash
curl -fsS http://127.0.0.1:8080/api/method/ping
# expect: {"message":"pong"}

curl -fsSI http://127.0.0.1:8080/lms
# expect: HTTP 200, Server nginx, Sales LMS HTML

curl -fsSI http://127.0.0.1:8080/lms/dashboard
# expect: 200 or redirect to login — NOT foreign JSON / uvicorn 403
```

**FAIL** if `server: uvicorn` or `Invalid authorization code`.

### 6. Public smoke checks (after LB → this VM `:8080`)

```bash
curl -fsS https://saleslms.infinitylearn.com/api/method/ping
curl -fsSI https://saleslms.infinitylearn.com/lms
```

**FAIL** if response shows `server: uvicorn` or auth-gateway JSON errors.

### 7. Import CRT schedule (required)

```bash
docker compose --env-file .env exec -w /home/frappe/frappe-bench backend \
  bench --site saleslms.infinitylearn.com execute lms.lms.sales_crt.preview_import --kwargs "{'use_bundled': 1}"

docker compose --env-file .env exec -w /home/frappe/frappe-bench backend \
  bench --site saleslms.infinitylearn.com execute lms.lms.sales_crt.import_schedule --kwargs "{'use_bundled': 1}"
```

Or upload a newer workbook at `/lms/crt/import` (dry-run first).

### 8. App smoke (browser)

1. Open `https://saleslms.infinitylearn.com/lms`
2. Login: `Administrator` / `ADMIN_PASSWORD`
3. Desk → Learning workspace loads
4. Sales CRT course and `/lms/crt` show Day 1 … Day N
5. Desk → Email Account exists (SMTP bootstrap)

### 9. Security (automatic on boot)

Set these in prod `.env` **before** step 4. The backend entrypoint applies them on every start:

| Variable | Prod value |
|----------|------------|
| `DEVELOPER_MODE` | `0` |
| `LMS_ALLOW_GUEST_ACCESS` | `0` |
| `LMS_DISABLE_SIGNUP` | `1` |
| `ALLOW_DEMO_LEARNER` | `0` |

`DEVELOPER_MODE=0` also blocks weak `ADMIN_PASSWORD=admin` on first site create.

Optional verify after boot:

```bash
docker compose --env-file .env exec -w /home/frappe/frappe-bench backend \
  bench --site saleslms.infinitylearn.com execute lms.lms.setup_security.ensure_lms_security_from_env
```

Do **not** run `ensure_demo_learner` on prod (`ALLOW_DEMO_LEARNER=0` disables it).

Before step 3 (build), run locally (optional):

```bash
bash scripts/check-secrets.sh
```

### 10. Backup

```bash
docker volume ls | grep sales
```

| What | Where |
|------|--------|
| Site files | Docker volume `sales_sites` |
| App data | AWS MariaDB database `salesapp` |
| Redis | Volume `sales_redis_data` (cache only) |

---

## Later updates

```bash
cd <VM_PATH>/sales_lms
git pull origin main

docker compose --env-file .env build backend
docker compose --env-file .env build frontend
docker compose --env-file .env up -d

curl -fsS http://127.0.0.1:8080/api/method/ping
```

Re-run step **7** only when the CRT Excel workbook changed.

---

## Ops commands

```bash
docker compose --env-file .env ps
docker compose --env-file .env logs -f backend
docker compose --env-file .env logs -f frontend
docker compose --env-file .env restart backend
docker compose --env-file .env exec backend bash

docker compose --env-file .env exec -w /home/frappe/frappe-bench backend \
  bench --site saleslms.infinitylearn.com console
```

---

## Day-0 cutover order (one line)

VM prep → clone → `.env` (incl. security vars) → build backend → build frontend → `up -d` → local verify → LB to `:8080` → public verify → CRT Excel import → login test.
