# Multi-stage build for Project Sally

# Stage 1: PostgreSQL + TimescaleDB base
FROM timescaledb/timescaledb:latest-pg15 as database

# Install additional utilities
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create application user and database
RUN useradd -m -s /bin/bash stock_user

# Stage 2: Python application environment
FROM python:3.11-slim as application

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -s /bin/bash stock_user

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY .env.example ./.env

# Set permissions
RUN chown -R stock_user:stock_user /app

# Switch to non-root user
USER stock_user

# Default command
CMD ["python", "-m", "src"]
