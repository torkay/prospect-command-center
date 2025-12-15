# API Reference

Base URL (local): `http://localhost:8000/api/v1`

## Search

- `POST /search` – Start async search
  - Body: `{ "business_type": str, "location": str, "limit": int, ... }`
  - Returns: `{ "job_id": str, "status": "pending" }`

- `POST /search/sync` – Run search synchronously
  - Returns results directly (blocks until complete)

- `GET /jobs` – List recent jobs
- `GET /jobs/{job_id}` – Get job details/status
- `DELETE /jobs/{job_id}` – Cancel or delete a job
- `POST /jobs/{job_id}/export/sheets` – Export job results to Google Sheets

## Prospects

- `GET /prospects` – List prospects
  - Filters: `status`, `campaign_id`, `search_id`, `q`
  - Sorting: `sort` (priority, fit, opportunity, created_at), `order` (asc/desc)

- `GET /prospects/{id}` – Get a prospect
- `PATCH /prospects/{id}` – Update fields (e.g., `status`, `notes`)
- `POST /prospects/{id}/skip` – Mark as skipped
- `DELETE /prospects/{id}` – Remove a prospect
- `POST /prospects/bulk-update` – Bulk status update

## Dashboard

- `GET /dashboard/summary` – KPI summary
- `GET /dashboard/activity` – Recent activity feed
- Additional analytical endpoints are available (see OpenAPI docs)

## Config

- `GET /config` – Current configuration and health (SerpAPI/Sheets)
- `PATCH /config` – Update configuration values
- `GET /health` – Health check

## WebSocket

- `WS /ws/jobs/{job_id}` – Real‑time progress stream for a job

OpenAPI docs are available at `/docs` (Swagger UI) and `/redoc`.

