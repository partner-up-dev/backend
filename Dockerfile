# syntax=docker/dockerfile:1

# ===== Build Stage =====
FROM python:3.12-slim AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install PDM
RUN pip install pdm

# Copy dependency files
COPY pyproject.toml pdm.lock* ./

# Export dependencies to requirements.txt and install
# If pdm.lock exists, use it; otherwise install from pyproject.toml
RUN pdm lock --prod 2>/dev/null || true && \
    pdm export --prod -o requirements.txt --without-hashes && \
    pip install --prefix=/install -r requirements.txt


# ===== Production Stage =====
FROM python:3.12-slim AS production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    ENV=production

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r appgroup && useradd -r -g appgroup appuser

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

# Create logs directory for gunicorn
RUN mkdir -p logs && chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/heartbeat')" || exit 1

# Run the application with uvicorn
CMD ["python", "-m", "uvicorn", "run:app", "--host", "0.0.0.0", "--port", "8000"]
