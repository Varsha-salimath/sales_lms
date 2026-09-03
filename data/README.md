# CRT curriculum data (not in git)

Place **`CRT-Schedule.xlsx`** here before **`docker compose build backend`**. The file is copied into the backend Docker image and auto-imported on site boot.

This workbook contains internal SharePoint, form, and ops links — **do not commit it** to git.

Obtain the current file from your team secure share / IL content owner.

```bash
# After copying the workbook:
docker compose --env-file .env build backend
docker compose --env-file .env exec -w /home/frappe/frappe-bench backend \
  bench --site <SITE_NAME> execute lms.lms.sales_crt.import_schedule --kwargs "{'use_bundled': 1}"
```

Alternatively, upload the workbook in the app: `/lms/crt/import` (dry-run first).
