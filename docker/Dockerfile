FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Install package in editable mode
RUN pip install -e .

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Environment
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/v1/health || exit 1

# Run
CMD ["uvicorn", "prospect.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
