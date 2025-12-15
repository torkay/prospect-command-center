# Scoring Methodology

Prospect Command Center computes a Priority score from Fit and Opportunity components. Defaults can be adjusted via YAML config or API.

## Priority

```
Priority = Fit × 0.4 + Opportunity × 0.6
```

## Fit (0–100)

Measures reachability and quality:
- Website present
- Phone present
- Email present
- Found in Maps/Local Pack
- Rating ≥ 4.0
- Reviews ≥ 10
- Running ads
- Organic top 10

## Opportunity (0–100)

Measures marketing gaps:
- No Google Analytics
- No Facebook Pixel
- No booking system
- No email visible
- DIY CMS
- Slow site
- Poor SEO ranking
- Already running ads (negative weight)

## Configuration

Weights and thresholds are defined in `config.example.yaml` and can be set via the API (`/api/v1/config`).

