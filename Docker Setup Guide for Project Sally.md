# Docker Setup Guide for Project Sally

This guide explains how to set up and run Project Sally using Docker on Mac and Windows.

## Why Docker?

Docker provides:
- **Consistency**: Same environment on Mac, Windows, and production servers
- **Isolation**: Database and Python environment are completely isolated
- **Reproducibility**: Anyone can run the project with a single command
- **Scalability**: Easy to add services, scale, and deploy to cloud
- **Industry Standard**: Used by hedge funds, fintech companies, and tech giants

## Prerequisites

### Mac Setup

1. **Install Docker Desktop for Mac**
   - Download from: https://www.docker.com/products/docker-desktop
   - Choose the appropriate version (Intel or Apple Silicon)
   - Install and launch Docker Desktop

2. **Verify Installation**
   ```bash
   docker --version
   docker-compose --version
   ```

### Windows Setup

1. **Install Docker Desktop for Windows**
   - Download from: https://www.docker.com/products/docker-desktop
   - Requires Windows 10/11 Pro, Enterprise, or Education
   - Install and launch Docker Desktop

2. **Enable WSL 2 (Windows Subsystem for Linux)**
   - Docker Desktop for Windows uses WSL 2 backend
   - Follow: https://docs.microsoft.com/en-us/windows/wsl/install

3. **Verify Installation**
   ```bash
   docker --version
   docker-compose --version
   ```

## Quick Start

### 1. Clone/Navigate to Project

```bash
cd ~/StockPickingSystem
```

### 2. Configure Environment (Optional)

The project comes with default settings, but you can customize:

```bash
cp .env.example .env
# Edit .env if needed (optional)
```

### 3. Start Services

```bash
docker-compose up -d
```

This command:
- Builds the Docker images
- Starts PostgreSQL + TimescaleDB container
- Starts Python application container
- Creates persistent data volume

### 4. Verify Services Are Running

```bash
docker-compose ps
```

Expected output:
```
NAME                  STATUS              PORTS
stock_picking_db      Up (healthy)        5432->5432/tcp
stock_picking_app     Up                  -
```

### 5. Connect to Application Container

```bash
docker-compose exec app bash
```

Now you're inside the container with Python and all dependencies installed.

### 6. Initialize Database

Inside the container:

```bash
python scripts/init_db.py --create
```

This creates all tables in PostgreSQL.

### 7. Test Setup

Inside the container:

```bash
python scripts/test_setup.py
```

Expected output: All tests should pass ✓

## Common Commands

### View Logs

```bash
# View all logs
docker-compose logs -f

# View only database logs
docker-compose logs -f database

# View only app logs
docker-compose logs -f app
```

### Connect to Database Directly

From your Mac/Windows terminal:

```bash
psql -h localhost -U stock_user -d stock_picking_system
```

Password: `secure_password_123` (or whatever you set in .env)

### Stop Services

```bash
docker-compose stop
```

### Start Services Again

```bash
docker-compose start
```

### Remove Everything (WARNING!)

```bash
docker-compose down -v
```

This removes containers and volumes. Data will be lost!

### Rebuild Images

If you change requirements.txt or Dockerfile:

```bash
docker-compose build --no-cache
docker-compose up -d
```

## Development Workflow

### Working on Mac

1. **Start containers**
   ```bash
   docker-compose up -d
   ```

2. **Connect to app container**
   ```bash
   docker-compose exec app bash
   ```

3. **Run Python scripts**
   ```bash
   python scripts/test_setup.py
   python scripts/init_db.py --create
   ```

4. **Edit code** on your Mac (files are mounted)
   - Changes in `src/`, `scripts/` are reflected in container
   - No need to rebuild

5. **Stop when done**
   ```bash
   docker-compose down
   ```

### Switching to Windows

1. **Clone the same repository** (or sync via Git)

2. **Start containers** (same commands work!)
   ```bash
   docker-compose up -d
   ```

3. **Everything works identically** - no setup needed!

## Troubleshooting

### "Docker daemon is not running"

**Mac**: Open Docker Desktop application  
**Windows**: Open Docker Desktop application

### "Port 5432 already in use"

Change the port in `docker-compose.yml`:
```yaml
ports:
  - "5433:5432"  # Use 5433 instead
```

Update `.env`:
```
DB_PORT=5433
```

### "Cannot connect to database"

1. Check if database is healthy:
   ```bash
   docker-compose ps
   ```

2. Check database logs:
   ```bash
   docker-compose logs database
   ```

3. Wait a few seconds - database may still be initializing

### "Permission denied" errors

On Mac/Linux, you might need sudo:
```bash
sudo docker-compose up -d
```

Or add your user to docker group:
```bash
sudo usermod -aG docker $USER
```

### "Out of disk space"

Docker images and volumes can take space. Clean up:
```bash
docker system prune -a
```

## Environment Variables

Key variables in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| DB_HOST | localhost | Database host |
| DB_PORT | 5432 | Database port |
| DB_USER | stock_user | Database user |
| DB_PASSWORD | secure_password_123 | Database password |
| DB_NAME | stock_picking_system | Database name |
| DATA_PROVIDER | yfinance | Data source |
| ENVIRONMENT | development | Environment mode |
| LOG_LEVEL | INFO | Logging level |
| DEBUG | True | Debug mode |

## Docker Architecture

```
┌─────────────────────────────────────────┐
│         Docker Compose Network          │
├─────────────────────────────────────────┤
│                                         │
│  ┌──────────────────┐  ┌─────────────┐ │
│  │   PostgreSQL +   │  │   Python    │ │
│  │   TimescaleDB    │  │ Application │ │
│  │   Container      │  │ Container   │ │
│  │                  │  │             │ │
│  │ Port: 5432       │  │ Volumes:    │ │
│  │ Volume: Data     │  │ src/        │ │
│  │ Healthy Check: ✓ │  │ scripts/    │ │
│  │                  │  │ logs/       │ │
│  └──────────────────┘  └─────────────┘ │
│         ▲                    │          │
│         └────────────────────┘          │
│         (Network: stock_network)        │
└─────────────────────────────────────────┘
```

## Performance Tips

### Mac with Apple Silicon

Docker Desktop for Mac with Apple Silicon is optimized. No special configuration needed.

### Windows with WSL 2

1. Allocate more resources to WSL 2:
   - Open `%USERPROFILE%\.wslconfig`
   - Add:
     ```
     [wsl2]
     memory=4GB
     processors=4
     ```

2. Store project on WSL filesystem (not Windows filesystem) for better performance

### Database Performance

For large datasets, consider:
- Increasing PostgreSQL shared_buffers
- Adding indexes for frequent queries
- Using TimescaleDB compression for old data

## Next Steps

1. ✅ Install Docker Desktop
2. ✅ Run `docker-compose up -d`
3. ✅ Connect and initialize database
4. ✅ Run test suite
5. ⏳ Start ingesting data (Phase 1, Week 3-4)

## Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [TimescaleDB Documentation](https://docs.timescaledb.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

## Support

If you encounter issues:
1. Check logs: `docker-compose logs`
2. Verify Docker is running
3. Try rebuilding: `docker-compose build --no-cache`
4. Reset everything: `docker-compose down -v && docker-compose up -d`

---

**Last Updated**: February 27, 2026  
**Docker Version**: 20.10+  
**Docker Compose Version**: 2.0+
