# Deployment

## Railway (Recommended)

The repository includes `railway.toml` configured for Uvicorn and a persistent volume at `/data`.

Steps:
- Fork the repository on GitHub
- Create a new Railway project → Deploy from GitHub
- Set environment variable `SERPAPI_KEY`
- Your app starts at the generated domain

Health check: `/api/v1/health`

## Docker

### Build

```bash
make docker
```

### Compose (local)

```bash
docker compose -f docker/docker-compose.yml up
```

### Compose (beta/dev)

```bash
docker compose -f docker/docker-compose.beta.yml up
```

### Compose (prod)

`docker/docker-compose.prod.yml` is provided with an image reference for GHCR and resource limits.

## Environment Variables

- `SERPAPI_KEY` (required) – SerpAPI key for Google search
- `ALLOWED_ORIGINS` (optional) – CORS origins (comma‑separated), default `*`
- `DATABASE_URL` (optional) – Defaults to SQLite; Railway uses `/data`

## Verify

```bash
./scripts/verify-deployment.sh https://your-app.up.railway.app
```

