# DevOps — Sales LMS production deploy (POC)

VM path: `/var/www/saleslms`  
Domain: `https://saleslms.infinitylearn.com`  
Port: **8080** (LB → nginx frontend only)

## 1. Get code

```bash
cd /var/www/saleslms
git pull origin main
```

## 2. Production `.env`

```bash
cp .env.prod.example .env
chmod 600 .env
nano .env   # fill <placeholders> from secure credentials (see team)
```

**Required values (team provides):**

| Key | Notes |
|-----|--------|
| `ADMIN_PASSWORD` | Frappe Administrator login |
| `DB_HOST` | AWS RDS endpoint |
| `DB_PASSWORD` / `DB_ROOT_PASSWORD` | RDS `saleslms_admin` password; **single quotes** if password contains `$` |
| `REDIS_PASSWORD` | Any strong password (Compose Redis on VM) |
| `SMTP_USER` / `SMTP_PASSWORD` | AWS SES IAM SMTP credentials |
| `UPSTREAM_REAL_IP_ADDRESS` | Load balancer / reverse proxy IP or CIDR |

**Do not change for prod:**

- `COMPOSE_PROFILES=` — must be **empty**
- `REDIS_HOST=redis`, `REDIS_PORT=6379`, `REDIS_USERNAME=` — **empty username** (Compose Redis)
- Do **not** use Redis Cloud (Frappe 16 breaks)

**Pre-checks:**

```bash
nc -vz <DB_HOST> 3306
nc -vz email-smtp.ap-south-1.amazonaws.com 587
ls -la data/CRT-Schedule.xlsx
free -h
```

## 3. Build and start (backend first — ~10–15 min)

```bash
export DOCKER_BUILDKIT=1
docker compose --env-file .env build --no-cache backend
docker compose --env-file .env build frontend
docker compose --env-file .env up -d
docker compose --env-file .env ps
```

## 4. Smoke tests

```bash
curl -fsS http://127.0.0.1:8080/api/method/ping
curl -fsSI http://127.0.0.1:8080/lms
docker compose --env-file .env logs backend | grep -i "bundled CRT"
```

Expected containers: `sales_lms_frontend`, `sales_lms_backend`, `sales_lms_redis` — **no** `sales_lms_db`.

Full runbook: [PRODUCTION_DEPLOY.md](../PRODUCTION_DEPLOY.md)
