# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0-beta.1] - 2024-12-14

### Added
- Initial beta release
- SerpAPI integration for reliable Google search
- Playwright fallback for no-API usage
- Website enrichment (CMS, analytics, booking detection)
- Scoring engine (Fit + Opportunity + Priority)
- CSV, JSON, JSONL export formats
- Google Sheets export with formatting
- Power-user CLI with Click command groups
  - `prospect search` - Main search command
  - `prospect batch` - Batch processing from YAML
  - `prospect check` - Configuration validation
  - `prospect version` - Version info
  - `prospect web` - Start web server
- Technical web UI with dark theme
  - REST API at `/api/v1/*`
  - WebSocket real-time updates
  - OpenAPI documentation at `/docs`
  - Keyboard shortcuts (/, Esc, j/k, e)
- Docker deployment support
- GitHub Actions CI/CD

### Technical
- 121+ unit tests passing
- Pydantic v2 models
- Configurable scoring weights via YAML
- Parallel website enrichment
- Smart deduplication (Maps > Ads > Organic)
