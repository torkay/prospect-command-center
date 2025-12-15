# Architecture

## System Overview

The Prospect Command Center is a FastAPI application with a lightweight SPA frontend. It orchestrates SerpAPI searches, website enrichment, scoring, and persistence.

```
Frontend (SPA)
  ├─ Dashboard / Prospects / Campaigns / Detail
  └─ WebSocket progress updates
          │ REST + WS
          ▼
FastAPI Backend
  ├─ API v1 (search, jobs, prospects, campaigns, dashboard, config)
  ├─ WebSocket (/ws/jobs/{id})
  ├─ Scraper (SerpAPI client, query building)
  ├─ Enrichment (fetch website, detect analytics/pixel/CMS, contacts)
  ├─ Scoring (fit, opportunity, priority)
  └─ Database (SQLAlchemy, SQLite by default)
```

## Modules

- `prospect/scraper/` – SerpAPI client and helpers
- `prospect/enrichment/` – website fetching, contact extraction, technology detection
- `prospect/scoring/` – fit/opportunity scoring and notes
- `prospect/web/` – FastAPI app, API v1, WebSocket, templates, frontend
- `prospect/` – shared models, config, deduplication, export utilities

## API Surface

- `POST /api/v1/search` – start async search job
- `POST /api/v1/search/sync` – run search synchronously
- `GET /api/v1/jobs` – list recent jobs; `GET /api/v1/jobs/{id}` – status/details
- `GET /api/v1/prospects` – list with filters and sorting; CRUD via `/{id}` where applicable
- `GET /api/v1/dashboard/summary` – summary stats; additional analytics endpoints available
- `GET /api/v1/config` / `PATCH /api/v1/config` – read/update configuration
- `GET /api/v1/health` – health check
- `WS /ws/jobs/{id}` – real‑time progress

## Data Flow (Search)

1. User submits a search (business_type, location, limit/filters)
2. SerpAPI client fetches Ads, Maps, and Organic results
3. Deduplication merges sources and filters directories/spam
4. Optional enrichment fetches website and extracts signals
5. Scoring calculates Fit and Opportunity; Priority combines weights
6. Results are persisted and returned to the UI

## Database

SQLite by default (Railway uses persistent volume at `/data`). SQLAlchemy models live under `prospect/web/database.py`.

Key entities:
- Prospects: business core fields + signals + scores + status
- Jobs/Searches: background job tracking and metrics
- Campaigns: saved configurations and reruns

