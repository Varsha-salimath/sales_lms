# DevOps — production deploy (generic)

Use this as a short operator checklist. **Do not** put real hostnames, RDS endpoints, or passwords in git.

VM path: e.g. `/var/www/sales-lms`  
Public URL: your `HOST_NAME` from `.env`  
Port: **8080** (load balancer → nginx **frontend** only)

## 1. Get code

```bash
cd /var/www/sales-lms
git pull
```

## 2. Production `.env`

```bash
cp .env.prod.example .env
chmod 600 .env
# Edit .env — values from your secret store / internal runbook
```

Required keys: `ADMIN_PASSWORD`, `DB_*`, `REDIS_PASSWORD`, `SMTP_*`, `DEFAULT_SENDER`, `SITE_NAME`, `HOST_NAME`.

- `COMPOSE_PROFILES=` must be **empty** (external DB).
- Prefer Compose Redis (`REDIS_HOST=redis`) unless external Redis is validated with Frappe 16.

Pre-checks:

```bash
free -h
nc -vz <DB_HOST> 3306
nc -vz <SMTP_HOST> 587
```

## 3. Build and start

```bash
export DOCKER_BUILDKIT=1
docker compose --env-file .env build backend
docker compose --env-file .env build frontend
docker compose --env-file .env up -d
docker compose --env-file .env ps
```

## 4. Smoke tests

```bash
curl -fsS http://127.0.0.1:8080/api/method/ping
curl -fsSI http://127.0.0.1:8080/lms
```

Full checklist: [PRODUCTION_DEPLOY.md](../PRODUCTION_DEPLOY.md)
