# Deployment

## Railway (Recommended)

The repository includes `railway.toml` configured for Uvicorn and a persistent volume at `/data`.

Steps:
- Fork the repository on GitHub
- Create a new Railway project → Deploy from GitHub
- Set environment variable `SERPAPI_KEY`
- Your app starts at the generated domain

Health check: `/api/v1/health`

### Use GHCR Image on Railway

You can deploy the prebuilt image from GHCR instead of building from source:

- In Railway Dashboard: New Service → Deploy from Container Registry → GitHub → Select `ghcr.io/torkay/prospect-command-center`
- Choose the desired tag (e.g., `1.0.1` or `latest`)
- Add environment variable `SERPAPI_KEY`
- (Optional) Add `ALLOWED_ORIGINS=https://<your-domain>`
- Ensure a persistent volume is attached at `/data` for the SQLite DB

Alternatively, configure the provided GitHub Actions workflow with secrets to deploy on every tagged release.

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
