# Sales LMS — Production deploy

| Item | Value |
|------|--------|
| Bitbucket repo | `git@bitbucket.org:CodeRepoInfinitylearn/saleslms.git` |
| Branch | `main` |
| Prod domain | `saleslms.infinitylearn.com` |
| Site name (`SITE_NAME`) | `saleslms.infinitylearn.com` |
| VM path | `<VM_PATH>` e.g. `/var/www/sales-lms/sales_lms` |
| Database engine | **MariaDB 11.8.8** (AWS POC — confirmed; `DB_TYPE=mariadb`, port 3306) |
| Database (`DB_NAME` / `DB_USER`) | `saleslms` / `saleslms_admin` (AWS RDS POC) |
| DB host | `<DB_HOST>` AWS RDS endpoint (MariaDB 11.8.8) |
| App port | **8080** (LB → VM `:8080`) |
| Redis | Compose only — `REDIS_HOST=redis`, `REDIS_PORT=6379`, `REDIS_USERNAME=` empty |
| Login | `Administrator` / `ADMIN_PASSWORD` from `.env` |

**Never commit** `.env`.

Frappe uses `DB_TYPE=mariadb`. AWS POC database is **MariaDB 11.8.8** (confirmed by DevOps).

---

## Before you start

- VM: Docker Engine + Compose v2, Git access to Bitbucket, outbound MySQL `:3306` and SMTP `:587`.
- Prod `.env`: `COMPOSE_PROFILES=` (empty — no embedded MariaDB).
- `SITE_NAME` ≠ `DB_NAME` (site = domain, db = `saleslms` on AWS POC).
- `DB_ROOT_USERNAME` is RDS master user (`saleslms_admin` on POC — not necessarily `root`).
- Do **not** use Redis Cloud (Frappe 16 CLIENT TRACKING breaks).
- SMTP required — compose/entrypoint fail without `SMTP_*` and `DEFAULT_SENDER`.
- **CRT curriculum:** copy **`CRT-Schedule.xlsx`** into `data/` **before** `build backend` (not in git — see `data/README.md`). The file is **baked into the backend image** and **auto-imported on first boot** (idempotent).
- **Build VM:** **Minimum 4 GB RAM** (e.g. AWS `t3.medium`) for `docker compose build backend`. A **2 GB** instance fails Vite with **exit 134 (heap OOM)** even with swap. If stuck on 2 GB RAM, add a **second** swap file (`/swapfile2`, 8 GB) — do not recreate `/swapfile` if it already exists.
- Prod `.env`: escape `$` in passwords (wrap in single quotes) or Compose warns `The "c" variable is not set`.
- **AWS RDS:** set `DB_USE_SSL=1` when RDS has `require_secure_transport=ON` (error 3159 without SSL).

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
DB_HOST=<aws-rds-endpoint>
DB_PORT=3306
DB_NAME=saleslms
DB_USER=saleslms_admin
DB_PASSWORD='<rds-password>'
DB_ROOT_USERNAME=saleslms_admin
DB_ROOT_PASSWORD='<rds-password>'
DB_USE_SSL=1

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
free -h    # Mem total must be ≥3.8Gi before backend build (Vite needs 4GB Node heap)
nc -vz <DB_HOST> 3306
nc -vz email-smtp.ap-south-1.amazonaws.com 587
ls -la data/CRT-Schedule.xlsx
docker ps
```

If RAM is under 4 GB, add **extra swap** (use a **new file** if `/swapfile` already exists):

```bash
free -h
# Only if Swap total < 12G:
sudo fallocate -l 8G /swapfile2
sudo chmod 600 /swapfile2
sudo mkswap /swapfile2
sudo swapon /swapfile2
free -h
```

**Do not** run `fallocate` on `/swapfile` again if swap is already active (`Text file busy`).

### 1. Get code

```bash
git clone git@bitbucket.org:CodeRepoInfinitylearn/saleslms.git
cd <repo-folder>    # e.g. sales_lms under <VM_PATH>
git checkout main
git pull origin main
```

### 2. Create prod `.env` and CRT data

```bash
cp .env.prod.example .env
chmod 600 .env
# Edit .env — fill <placeholders>. DevOps: DB_HOST, DB_* passwords, ADMIN_PASSWORD, LB IP.
# SMTP keys from team. Use Compose Redis (REDIS_HOST=redis), not Redis Cloud.
# Wrap passwords containing $ in single quotes.
```

Copy the CRT workbook into the repo **before build** (required — build fails without it):

```bash
cp /path/from/secure-share/CRT-Schedule.xlsx data/CRT-Schedule.xlsx
ls -la data/CRT-Schedule.xlsx
```

### 3. Build images (backend first — ~10–15 min)

**Backend must succeed before frontend.** Backend build runs Vite (~10–15 min). OOM = exit 134/137 → VM must have **≥4 GB RAM** (`free -h` before build). Node heap is **4096 MB** in Dockerfile and `frontend/package.json`. Pull latest `main` before building.

```bash
export DOCKER_BUILDKIT=1
docker compose --env-file .env build --no-cache backend
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

### 7. CRT schedule (auto-import + manual fallback)

On first boot the entrypoint imports **`sales-crt`** from the image-baked Excel (`/opt/sales-lms/data/CRT-Schedule.xlsx`) if the course is empty.

Verify after `up -d`:

```bash
docker compose --env-file .env logs backend | grep -i "bundled CRT"
```

Manual re-import (only if auto-import failed or Excel was updated):

```bash
docker compose --env-file .env exec -w /home/frappe/frappe-bench backend \
  bench --site saleslms.infinitylearn.com execute lms.lms.sales_crt.import_bundled_schedule
```

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
