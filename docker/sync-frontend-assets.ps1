# After `yarn build` inside sales_lms_backend, nginx (sales_lms_frontend) still serves
# baked assets. Run this from repo root to copy apps/lms/lms/public and relink assets/lms.
$ErrorActionPreference = "Stop"
$backend = "sales_lms_backend"
$frontend = "sales_lms_frontend"
$public = "/home/frappe/frappe-bench/apps/lms/lms/public"
$staging = Join-Path $env:TEMP "sales_lms_public_sync"

if (Test-Path $staging) { Remove-Item -Recurse -Force $staging }
New-Item -ItemType Directory -Path $staging | Out-Null

Write-Host "Copying LMS public from $backend..."
docker cp "${backend}:${public}/." $staging
Write-Host "Installing into $frontend and linking assets/lms..."
docker cp "${staging}/." "${frontend}:${public}/"
docker exec -u root $frontend bash -c "chown -R frappe:frappe /home/frappe/frappe-bench/apps/lms/lms/public && ln -sfn /home/frappe/frappe-bench/apps/lms/lms/public /home/frappe/frappe-bench/assets/lms && test -f /home/frappe/frappe-bench/assets/lms/frontend/index.html && echo OK: assets/lms linked"
Remove-Item -Recurse -Force $staging
Write-Host "Done. Hard-refresh the browser (Ctrl+Shift+R)."
