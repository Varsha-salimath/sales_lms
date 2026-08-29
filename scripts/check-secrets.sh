#!/usr/bin/env bash
# Fail if secrets or dev scratch files are staged for commit.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"

failed=0

if git rev-parse --git-dir >/dev/null 2>&1; then
	staged="$(git diff --cached --name-only || true)"
	if echo "$staged" | grep -qx '.env'; then
		echo "BLOCKED: .env is staged — never commit secrets." >&2
		failed=1
	fi
	if echo "$staged" | grep -Eq '^data/_'; then
		echo "BLOCKED: data/_* dev scratch files are staged." >&2
		failed=1
	fi
	if echo "$staged" | grep -Eq 'CRT-Schedule\.xlsx|data/.*\.xlsx'; then
		echo "BLOCKED: CRT-Schedule.xlsx is staged — curriculum file must not be committed." >&2
		failed=1
	fi
else
	echo "WARN: not a git repository — skipping staged-file checks."
fi

for path in data/_audit_dump.json data/_sched_rest.txt; do
	if [[ -f "$path" ]]; then
		echo "WARN: remove dev scratch file before prod build: $path" >&2
	fi
done

if [[ "${COMPOSE_PROFILES:-}" != *embedded-db* && "${DEVELOPER_MODE:-0}" == "0" && "${ADMIN_PASSWORD:-admin}" == "admin" ]]; then
	if [[ -f .env ]]; then
		# shellcheck disable=SC1091
		source .env 2>/dev/null || true
		if [[ "${DEVELOPER_MODE:-0}" == "0" && "${ADMIN_PASSWORD:-admin}" == "admin" ]]; then
			echo "BLOCKED: prod .env must set strong ADMIN_PASSWORD when DEVELOPER_MODE=0." >&2
			failed=1
		fi
	fi
fi

exit "$failed"
