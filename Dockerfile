# Multi-stage build for Project Sally

# ── Stage 1: PostgreSQL + TimescaleDB ─────────────────────────────────────────
FROM timescaledb/timescaledb:latest-pg15 AS database

RUN apt-get update && apt-get install -y \
    curl wget git \
    && rm -rf /var/lib/apt/lists/*

# ── Stage 2: Python application ───────────────────────────────────────────────
FROM python:3.11-slim AS application

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential libpq-dev curl git \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash stock_user

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY scripts/ ./scripts/

# FIX: the original Dockerfile did `COPY .env.example ./.env`, which meant
# the container always started with the example file — silently ignoring
# whatever the developer put in their real .env on the host.
# Configuration is now supplied entirely via the `environment:` block in
# docker-compose.yml, so no .env file copy is needed here.

RUN chown -R stock_user:stock_user /app

USER stock_user

CMD ["python", "-m", "src"]
