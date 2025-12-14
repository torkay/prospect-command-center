# Prospect Scraper

A prospect discovery tool for marketing agencies. Searches Google via SerpAPI to find local businesses, analyzes their websites for marketing gaps, and outputs a scored, prioritized list of prospects.

## Features

- **Reliable Google Search** via SerpAPI (no CAPTCHA issues)
- **Comprehensive SERP Data**: Ads, Maps/Local Pack, and Organic results
- **Website Enrichment**: CMS detection, tracking pixels, contact info extraction
- **Smart Scoring**: Fit score (reachability) + Opportunity score (marketing gaps)
- **Multiple Export Formats**: CSV, JSON, JSONL, Google Sheets
- **Power User CLI**: Filtering, parallel processing, batch mode
- **Technical Web UI**: Dark theme, REST API, WebSocket updates
- **Docker Ready**: Production and beta deployment configs

## Quick Start

```bash
# Clone and setup
git clone https://github.com/torkay/prospect-scraper.git
cd prospect-scraper
./scripts/setup.sh

# Add your API key
echo "SERPAPI_KEY=your_key_here" >> .env

# Activate environment
source venv/bin/activate

# Run a search
prospect search "plumber" "Sydney" --limit 10
```

## Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Install browser for fallback scraping
playwright install chromium
```

## Setup

### Get a SerpAPI Key

1. Sign up at [SerpAPI](https://serpapi.com/) (100 free searches/month)
2. Copy your API key from the dashboard
3. Set it in your `.env` file:

```bash
cp .env.example .env
# Edit .env and add your SERPAPI_KEY
```

## CLI Usage

```bash
# Basic search
prospect search "buyer's agent" "Brisbane, QLD"

# With filtering
prospect search "plumber" "Sydney" --limit 50 --min-fit 40 --require-phone

# JSON output (pipeable to jq)
prospect search "accountant" "Melbourne" -f json -q | jq '.[:5]'

# Parallel enrichment
prospect search "dentist" "Perth" --parallel 5

# Skip enrichment (faster, API-only)
prospect search "real estate agent" "Adelaide" --skip-enrichment

# Export to Google Sheets
prospect search "lawyer" "Canberra" --sheets "Lawyer Prospects"

# Batch mode from YAML config
prospect batch config.yaml

# Check configuration
prospect check

# Start web UI
prospect web --port 8000
```

### Command Reference

| Command | Description |
|---------|-------------|
| `prospect search` | Search for prospects |
| `prospect batch` | Run batch from YAML config |
| `prospect check` | Validate configuration |
| `prospect version` | Show version info |
| `prospect web` | Start web server |

### Search Options

| Option | Description |
|--------|-------------|
| `--limit, -l` | Max results (default: 20) |
| `--output, -o` | Output file path |
| `--format, -f` | Format: csv, json, jsonl, table |
| `--skip-enrichment` | Skip website analysis |
| `--parallel` | Concurrent enrichment (1-10) |
| `--min-fit` | Minimum fit score (0-100) |
| `--min-opportunity` | Minimum opportunity score |
| `--min-priority` | Minimum priority score |
| `--require-phone` | Only include with phone |
| `--require-email` | Only include with email |
| `--sheets` | Export to Google Sheets |
| `--quiet, -q` | Suppress progress output |
| `--debug` | Enable debug logging |

## Web UI

Start the web server:

```bash
prospect web
# or
make run
```

Open http://localhost:8000

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/search` | POST | Start async search |
| `/api/v1/search/sync` | POST | Synchronous search |
| `/api/v1/jobs` | GET | List recent jobs |
| `/api/v1/jobs/{id}` | GET | Get job details |
| `/api/v1/jobs/{id}` | DELETE | Cancel/delete job |
| `/api/v1/jobs/{id}/results` | GET | Export results |
| `/api/v1/config` | GET/PATCH | Configuration |
| `/api/v1/health` | GET | Health check |
| `/ws/jobs/{id}` | WebSocket | Real-time updates |

API documentation available at `/docs` (Swagger UI) and `/redoc`.

## Scoring

### Fit Score (0-100)
Measures how easily you can reach and contact the prospect:

| Factor | Points |
|--------|--------|
| Has website | +15 |
| Has phone | +15 |
| Has email | +10 |
| Found in Maps | +15 |
| Good rating (4.0+) | +10 |
| Has reviews (10+) | +10 |
| Running ads | +10 |
| Organic top 10 | +15 |

### Opportunity Score (0-100)
Measures how much they could benefit from your services:

| Factor | Points |
|--------|--------|
| No website | +80 |
| No Google Analytics | +15 |
| No Facebook Pixel | +10 |
| No booking system | +15 |
| No contact email | +10 |
| Using weak CMS | +10 |
| Poor organic ranking | +20 |
| Already running ads | -10 |

## Docker

```bash
# Build image
make docker

# Run with docker-compose
docker-compose -f docker/docker-compose.yml up

# Beta testing
docker-compose -f docker/docker-compose.beta.yml up
```

## Development

```bash
# Install dev dependencies
make dev

# Run tests
make test

# Run tests with coverage
make test-cov

# Lint code
make lint

# Format code
make format
```

## Project Structure

```
prospect-scraper/
├── prospect/
│   ├── __init__.py
│   ├── api.py              # Library API
│   ├── cli.py              # Click CLI
│   ├── config.py           # Settings & YAML config
│   ├── models.py           # Data models
│   ├── dedup.py            # Deduplication
│   ├── export.py           # CSV/JSON export
│   ├── scraper/
│   │   ├── serpapi.py      # SerpAPI client
│   │   └── serp.py         # HTML parsing
│   ├── enrichment/
│   │   ├── crawler.py      # Website fetching
│   │   ├── contacts.py     # Email/phone extraction
│   │   └── technology.py   # CMS/tracking detection
│   ├── scoring/
│   │   ├── fit.py          # Fit score
│   │   ├── opportunity.py  # Opportunity score
│   │   └── notes.py        # Notes generation
│   ├── sheets/
│   │   └── client.py       # Google Sheets export
│   └── web/
│       ├── app.py          # FastAPI app
│       ├── api/v1/         # REST API
│       ├── ws/             # WebSocket
│       └── frontend/       # SPA UI
├── tests/
├── docker/
├── scripts/
├── .github/workflows/
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## Beta Testing

### Quick Start (One Command)

```bash
curl -sSL https://raw.githubusercontent.com/torkay/prospect-scraper/beta/scripts/beta-setup.sh | bash
```

### Manual Setup

```bash
# Clone beta branch
git clone -b beta https://github.com/torkay/prospect-scraper.git
cd prospect-scraper

# Run setup
./scripts/setup.sh

# Add your API key
echo "SERPAPI_KEY=your_key" >> .env

# Test
source venv/bin/activate
./scripts/quick-test.sh
```

### What to Test

1. **CLI Search**
   ```bash
   prospect search "buyer's agent" "Brisbane" --limit 10
   ```

2. **JSON Output**
   ```bash
   prospect search "plumber" "Sydney" -f json -q | jq '.[:3]'
   ```

3. **Web UI**
   ```bash
   make run
   # Open http://localhost:8000
   ```

4. **Filters**
   ```bash
   prospect search "accountant" "Melbourne" --min-fit 50 --require-phone
   ```

### Report Issues

Found a bug? [Open an issue](https://github.com/torkay/prospect-scraper/issues/new) with:
- What you tried
- What happened
- What you expected
- Your OS and Python version

---

## License

MIT - See [LICENSE](LICENSE)
