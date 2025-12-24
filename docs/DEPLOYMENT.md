# Deployment Guide

## Prerequisites

- Linux VPS (Ubuntu 20.04+ or Debian 11+)
- Minimum 8GB RAM (16GB+ recommended for large memory images)
- 100GB+ disk space
- Root or sudo access

## Quick Start

### 1. Clone Repository

```bash
git clone <repository-url> /opt/forensics-platform
cd /opt/forensics-platform
```

### 2. Run Deployment Script

```bash
chmod +x deploy/deploy.sh
sudo ./deploy/deploy.sh
```

This will:
- Install Docker and Docker Compose
- Install system dependencies
- Configure environment
- Build containers
- Start all services

### 3. Verify Installation

```bash
# Check all services are running
docker-compose ps

# Test API
curl http://localhost:8000/api/v1/health

# Access web interface
# Navigate to: http://YOUR_SERVER_IP
```

## Manual Deployment

### Step 1: Install System Dependencies

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### Step 2: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Generate secure secret key
openssl rand -hex 32

# Edit .env and update:
# - SECRET_KEY (use generated key above)
# - Database credentials
# - Storage paths
nano .env
```

### Step 3: Build and Start Services

```bash
# Build containers
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f
```

### Step 4: Initialize Database

```bash
# Run database migrations (when implemented)
docker-compose exec api alembic upgrade head

# Create admin user (when implemented)
docker-compose exec api python -m backend.scripts.create_admin
```

## Service Architecture

### Running Services

- **API Server** (port 8000): FastAPI application
- **Nginx** (port 80/443): Reverse proxy and static files
- **PostgreSQL** (port 5432): Database
- **Redis** (port 6379): Message broker and cache
- **Celery Worker**: Background task processor
- **Flower** (port 5555): Celery monitoring dashboard

### Storage Layout

```
/var/forensics/
├── uploads/          # Uploaded memory images
├── artifacts/        # Extracted artifacts
├── results/          # JSON plugin outputs
└── logs/            # Application logs
```

## Configuration

### Environment Variables

Critical settings in `.env`:

```bash
# Security
SECRET_KEY=<64-char-hex-string>

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/db

# Storage
STORAGE_ROOT=/var/forensics
MAX_UPLOAD_SIZE_GB=20

# Workers
CELERY_WORKER_CONCURRENCY=2
```

### Resource Limits

Adjust in `docker-compose.yml`:

```yaml
worker:
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 8G
      reservations:
        memory: 4G
```

## Production Hardening

### 1. SSL/TLS Configuration

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d yourdomain.com

# Auto-renewal
sudo crontab -e
# Add: 0 3 * * * certbot renew --quiet
```

Update `docker/nginx.conf` to enable HTTPS block.

### 2. Firewall Configuration

```bash
# UFW configuration
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### 3. Database Security

```bash
# Change default passwords in docker-compose.yml
# Use strong passwords (16+ chars, random)

# Restrict PostgreSQL access
# Edit docker-compose.yml to not expose port 5432 externally
```

### 4. Log Rotation

```bash
# Configure Docker logging
# Edit /etc/docker/daemon.json:
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}

sudo systemctl restart docker
```

## Monitoring

### Health Checks

```bash
# API health
curl http://localhost:8000/api/v1/health

# Database
docker-compose exec postgres pg_isready

# Redis
docker-compose exec redis redis-cli ping

# Celery workers
curl http://localhost:5555
```

### Log Access

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f worker

# Last 100 lines
docker-compose logs --tail=100 api
```

### Celery Monitoring

Access Flower dashboard: `http://YOUR_SERVER:5555`

Monitor:
- Active workers
- Task queue lengths
- Task success/failure rates
- Worker resource usage

## Backup Strategy

### Database Backup

```bash
# Create backup
docker-compose exec postgres pg_dump -U forensics forensics_db > backup.sql

# Restore backup
docker-compose exec -T postgres psql -U forensics forensics_db < backup.sql
```

### Storage Backup

```bash
# Backup uploaded images and artifacts
tar -czf forensics-storage-$(date +%Y%m%d).tar.gz /var/forensics/

# Restore
tar -xzf forensics-storage-20231224.tar.gz -C /
```

### Automated Backups

```bash
# Add to crontab
0 2 * * * /opt/forensics-platform/scripts/backup.sh
```

## Scaling

### Horizontal Scaling

Add more Celery workers:

```bash
docker-compose up -d --scale worker=4
```

### Load Balancing

For multi-node deployment:

1. Run API servers on multiple nodes
2. Use external PostgreSQL cluster
3. Use external Redis cluster
4. Configure Nginx load balancing

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker-compose logs <service>

# Check container status
docker-compose ps

# Restart service
docker-compose restart <service>
```

### Out of Disk Space

```bash
# Check usage
df -h
du -sh /var/forensics/*

# Clean old artifacts
docker-compose exec api python -m backend.scripts.cleanup --days=30

# Clean Docker resources
docker system prune -a
```

### Memory Issues

```bash
# Check worker memory
docker stats

# Reduce concurrent tasks
# Edit .env: CELERY_WORKER_CONCURRENCY=1

# Increase worker restart frequency
# Edit backend/workers/celery_app.py: worker_max_tasks_per_child=5
```

### Plugin Timeouts

```bash
# Increase timeout in .env
VOL3_TIMEOUT_SECONDS=7200

# Restart workers
docker-compose restart worker
```

## Updating

### Update Application

```bash
cd /opt/forensics-platform
git pull
docker-compose down
docker-compose build
docker-compose up -d
```

### Update Dependencies

```bash
# Update requirements.txt
docker-compose build --no-cache
docker-compose up -d
```

## Maintenance

### Regular Tasks

- Review logs weekly
- Monitor disk usage
- Check worker health
- Update dependencies monthly
- Rotate backups
- Review security advisories

### Performance Optimization

- Tune PostgreSQL settings
- Configure Redis persistence
- Optimize Nginx caching
- Monitor slow queries
- Profile worker performance

## Support

For issues or questions:
- Check logs first
- Review configuration
- Consult documentation
- Submit issue with logs and config (redact secrets!)
