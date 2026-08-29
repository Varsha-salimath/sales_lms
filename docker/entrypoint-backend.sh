#!/usr/bin/env bash
# Backend entrypoint: configure Redis/Postgres → ensure site → run processes.
set -euo pipefail

cd /home/frappe/frappe-bench
export PATH="${PATH:-/usr/local/bin:/usr/bin:/bin}"

SITE_NAME="${SITE_NAME:-sales.localhost}"
HOST_NAME="${HOST_NAME:-http://localhost:8080}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin}"
DB_TYPE=postgres
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-salesapp}"
DB_USER="${DB_USER:-salesapp}"
DB_PASSWORD="${DB_PASSWORD:?Set DB_PASSWORD}"
DB_ROOT_USERNAME="${DB_ROOT_USERNAME:-postgres}"
DB_ROOT_PASSWORD="${DB_ROOT_PASSWORD:-${DB_PASSWORD}}"
REDIS_PASSWORD="${REDIS_PASSWORD:-sales_local_redis}"
REDIS_USERNAME="${REDIS_USERNAME:-}"
REDIS_HOST="${REDIS_HOST:-redis}"
REDIS_PORT="${REDIS_PORT:-6379}"
SOCKETIO_PORT="${SOCKETIO_PORT:-9000}"
SMTP_HOST="${SMTP_HOST:?Set SMTP_HOST}"
SMTP_PORT="${SMTP_PORT:-587}"
SMTP_USER="${SMTP_USER:?Set SMTP_USER}"
SMTP_PASSWORD="${SMTP_PASSWORD:?Set SMTP_PASSWORD}"
DEFAULT_SENDER="${DEFAULT_SENDER:?Set DEFAULT_SENDER}"
DEFAULT_SENDER_NAME="${DEFAULT_SENDER_NAME:-Sales LMS}"
SMTP_TLS="${SMTP_TLS:-1}"
SMTP_SSL="${SMTP_SSL:-0}"

wait_tcp() {
	local host="$1" port="$2" label="$3" tries="${4:-90}"
	echo "Waiting for ${label} at ${host}:${port}..."
	for i in $(seq 1 "${tries}"); do
		if /home/frappe/frappe-bench/env/bin/python - <<PY
import socket
s = socket.socket()
s.settimeout(2)
try:
	s.connect(("${host}", int("${port}")))
except Exception:
	raise SystemExit(1)
finally:
	s.close()
PY
		then
			echo "${label} is up."
			return 0
		fi
		sleep 2
	done
	echo "FATAL: ${label} not reachable at ${host}:${port}" >&2
	exit 1
}

wait_tcp "${DB_HOST}" "${DB_PORT}" "postgres"
wait_tcp "${REDIS_HOST}" "${REDIS_PORT}" "redis"

ls -1 apps > sites/apps.txt

# Build redis://[username]:password@host:port?protocol=3 (ACL user+pass for prod)
redis_default_url="$(
	/home/frappe/frappe-bench/env/bin/python - <<PY
from urllib.parse import quote
user = """${REDIS_USERNAME}""".strip()
password = """${REDIS_PASSWORD}"""
host = """${REDIS_HOST}"""
port = """${REDIS_PORT}"""
auth = f"{quote(user, safe='')}:{quote(password, safe='')}" if user else f":{quote(password, safe='')}"
print(f"redis://{auth}@{host}:{port}?protocol=3")
PY
)"

if [[ -z "${REDIS_CACHE:-}" ]]; then
	REDIS_CACHE="${redis_default_url}"
fi
if [[ -z "${REDIS_QUEUE:-}" ]]; then
	REDIS_QUEUE="${redis_default_url}"
fi
if [[ -z "${REDIS_SOCKETIO:-}" ]]; then
	REDIS_SOCKETIO="${redis_default_url}"
fi

bench set-config -g db_type postgres || true
bench set-config -g db_host "${DB_HOST}" || true
bench set-config -gp db_port "${DB_PORT}" || true
bench set-config -g redis_cache "${REDIS_CACHE}"
bench set-config -g redis_queue "${REDIS_QUEUE}"
bench set-config -g redis_socketio "${REDIS_SOCKETIO}"
bench set-config -gp socketio_port "${SOCKETIO_PORT}"
bench set-config -g chromium_path /usr/bin/chromium-headless-shell || true

bootstrap_smtp() {
	echo "Bootstrapping SMTP (${SMTP_HOST}:${SMTP_PORT} as ${DEFAULT_SENDER})..."
	if bench --site "${SITE_NAME}" execute lms.lms.setup_email.ensure_outgoing_email_from_env; then
		echo "SMTP Email Account configured."
		return 0
	fi
	echo "FATAL: SMTP bootstrap failed — check SMTP_* / DEFAULT_SENDER in .env" >&2
	exit 1
}

ensure_site() {
	if [[ -d "sites/${SITE_NAME}" ]]; then
		echo "Site ${SITE_NAME} exists — migrate."
		bench use "${SITE_NAME}" || true
		bench --site "${SITE_NAME}" migrate || true
		bench --site "${SITE_NAME}" set-config host_name "${HOST_NAME}" || true
		bootstrap_smtp
		return 0
	fi

	echo "Creating site ${SITE_NAME} (postgres db=${DB_NAME})..."
	# Frappe postgres root connection uses database named after DB_ROOT_USERNAME.
	/home/frappe/frappe-bench/env/bin/python - <<PY
import psycopg2
from psycopg2 import sql

root_user = "${DB_ROOT_USERNAME}"
conn = psycopg2.connect(
	host="${DB_HOST}",
	port=int("${DB_PORT}"),
	user=root_user,
	password="${DB_ROOT_PASSWORD}",
	dbname="postgres",
	connect_timeout=10,
)
conn.autocommit = True
cur = conn.cursor()
cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (root_user,))
if not cur.fetchone():
	cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(root_user)))
	print(f"Created bootstrap database {root_user}")
else:
	print(f"Bootstrap database already exists: {root_user}")
# Ensure site DB exists when name differs from root user
site_db = "${DB_NAME}"
if site_db != root_user:
	cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (site_db,))
	if not cur.fetchone():
		cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(site_db)))
		print(f"Created site database {site_db}")
cur.close()
conn.close()
PY

	bench new-site "${SITE_NAME}" \
		--db-type postgres \
		--db-name "${DB_NAME}" \
		--db-host "${DB_HOST}" \
		--db-port "${DB_PORT}" \
		--db-root-username "${DB_ROOT_USERNAME}" \
		--db-root-password "${DB_ROOT_PASSWORD}" \
		--admin-password "${ADMIN_PASSWORD}" \
		--set-default

	bench --site "${SITE_NAME}" install-app payments
	bench --site "${SITE_NAME}" install-app lms
	bench --site "${SITE_NAME}" set-config host_name "${HOST_NAME}"
	bench --site "${SITE_NAME}" set-config developer_mode 1 || true
	bench --site "${SITE_NAME}" clear-cache
	bench use "${SITE_NAME}"
	bootstrap_smtp
	echo "Site ready: ${SITE_NAME}"
	echo "NOTE: CRT course content is empty until Excel import runs."
}

ensure_site

# Frappe sites/assets is a symlink to /home/frappe/frappe-bench/assets (NOT on the
# sites volume). Ensure LMS public assets are linked in this container too.
ensure_lms_assets() {
	mkdir -p /home/frappe/frappe-bench/assets
	ln -sfn /home/frappe/frappe-bench/apps/lms/lms/public /home/frappe/frappe-bench/assets/lms
	mkdir -p apps/lms/www
	if [[ -f apps/lms/lms/public/frontend/index.html ]]; then
		cp -f apps/lms/lms/public/frontend/index.html apps/lms/www/_lms.html
	fi
	echo "LMS assets linked at assets/lms -> apps/lms/lms/public"
}
ensure_lms_assets

echo "Starting backend (worker, schedule, socketio, serve)..."
bench worker --queue short,default,long &
bench schedule &
node /home/frappe/frappe-bench/apps/frappe/socketio.js &
exec bench serve --port 8000
