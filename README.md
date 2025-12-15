# Prospect Command Center

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template?template=https://github.com/torkay/prospect-command-center)

Intelligent prospect discovery and qualification for marketing agencies.

Prospect Command Center combines automated Google search (via SerpAPI) with website enrichment and a scoring engine to surface high‑value prospects and manage them through a simple pipeline.

• Smart discovery • Intelligent scoring • Pipeline workflow • Modern web UI

## Features

- Smart discovery across Ads, Maps, and Organic results
- Website enrichment (CMS, analytics/pixel, emails/phones, booking)
- Three scores: Fit, Opportunity, and Priority (weighted)
- Web UI with real‑time progress, API docs, and keyboard shortcuts
- CLI for power users (batch mode, filters, multiple formats)
- Exports to CSV/JSON/JSONL and Google Sheets
- Docker and Railway deployment ready

## Quick Start

```bash
# Clone and setup
git clone https://github.com/torkay/prospect-command-center.git
cd prospect-command-center
./scripts/setup.sh

# Configure API key
cp .env.example .env
edit .env  # add SERPAPI_KEY

# Activate environment
source venv/bin/activate

# Run the web UI
make run
# open http://localhost:8000

# Or run a CLI search
prospect search "plumber" "Sydney" --limit 10
```

## Installation

```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e ".[dev]"
playwright install chromium
```

## CLI Usage

```bash
# Basic search
prospect search "buyer's agent" "Brisbane, QLD"

# Filtered and JSON output
prospect search "accountant" "Melbourne" -f json -q | jq '.[:5]'

# Faster (skip enrichment)
prospect search "real estate agent" "Adelaide" --skip-enrichment

# Export to Google Sheets
prospect search "lawyer" "Canberra" --sheets "Lawyer Prospects"

# Batch from YAML config
prospect batch config.yaml

# Start the web server
prospect web --port 8000
```

Key options: `--limit`, `--format`, `--parallel`, `--min-fit`, `--min-opportunity`, `--min-priority`, `--require-phone`, `--require-email`, `--skip-enrichment`, `--sheets`.

## Web UI & API

- App: `http://localhost:8000`
- OpenAPI: `/docs` (Swagger) and `/redoc`
- WebSocket progress: `/ws/jobs/{id}`

Core endpoints (see docs/API.md for full details):
- `POST /api/v1/search` – start async search
- `POST /api/v1/search/sync` – synchronous search
- `GET /api/v1/jobs` – list recent jobs
- `GET /api/v1/prospects` – list prospects
- `GET /api/v1/dashboard/summary` – summary stats
- `GET /api/v1/config` – read config; `PATCH /api/v1/config` – update

## Scoring Overview

Priority = Fit × 0.4 + Opportunity × 0.6 (default weights)

- Fit: reachability and quality (website, phone/email, maps, rating, reviews, ads, organic)
- Opportunity: marketing gaps (no analytics/pixel/booking/email, DIY CMS, slow site, poor SEO)

See docs/SCORING.md for details and configuration options.

## Deployment

### Railway

- Repo includes `railway.toml` and a persistent volume at `/data`
- Set `SERPAPI_KEY` in Railway variables
- Default start: `uvicorn prospect.web.app:app --host 0.0.0.0 --port $PORT`

### Docker

```bash
# Build
make docker

# Local compose
docker compose -f docker/docker-compose.yml up

# Beta compose
docker compose -f docker/docker-compose.beta.yml up
```

### Container Image (GHCR)

Images are published to GitHub Container Registry on tagged releases.

```bash
# Pull specific version
docker pull ghcr.io/torkay/prospect-command-center:1.0.0

# Or latest (from latest tagged release)
docker pull ghcr.io/torkay/prospect-command-center:latest

# Run
docker run -p 8000:8000 -e SERPAPI_KEY=your_key ghcr.io/torkay/prospect-command-center:1.0.0
```

To publish a new image: push a semver tag, e.g. `v1.0.1`.

## Project Structure

```
prospect-command-center/
├── prospect/
│   ├── cli.py              # CLI
│   ├── api.py              # Library API
│   ├── config.py           # Settings & YAML config
│   ├── models.py           # Data models
│   ├── dedup.py            # Deduplication
│   ├── export.py           # CSV/JSON export
│   ├── scraper/            # SerpAPI client & helpers
│   ├── enrichment/         # Website analysis
│   ├── scoring/            # Fit/Opportunity engine
│   └── web/                # FastAPI app + SPA
├── docs/                   # Architecture, API, deployment
├── docker/                 # Dockerfiles and compose
├── scripts/                # Setup and utilities
├── tests/                  # Unit/integration tests
├── requirements.txt        # Dependencies (runtime)
├── pyproject.toml          # Package metadata
└── README.md
```

## Documentation

- Architecture: `docs/ARCHITECTURE.md`
- API Reference: `docs/API.md`
- Deployment: `docs/DEPLOYMENT.md`
- Scoring Methodology: `docs/SCORING.md`

## License

MIT – see `LICENSE`
