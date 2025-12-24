# Quick Reference - Forensics Platform Operations

## Common Commands

### Start Services
```bash
docker-compose up -d
```

### Stop Services
```bash
docker-compose down
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f worker

# Last 100 lines
docker-compose logs --tail=100 worker
```

### Check Status
```bash
# All containers
docker-compose ps

# API health
curl http://localhost:8000/api/v1/health

# Worker monitoring
open http://localhost:5555  # Flower dashboard
```

### Restart Services
```bash
# All services
docker-compose restart

# Single service
docker-compose restart worker
```

### Scale Workers
```bash
# Increase to 4 workers
docker-compose up -d --scale worker=4

# Decrease to 1 worker
docker-compose up -d --scale worker=1
```

## Troubleshooting

### Worker Not Processing Jobs

```bash
# Check worker logs
docker-compose logs -f worker

# Restart workers
docker-compose restart worker

# Check Redis connection
docker-compose exec redis redis-cli ping
```

### API Not Responding

```bash
# Check API logs
docker-compose logs -f api

# Restart API
docker-compose restart api

# Check if port 8000 is available
netstat -tlnp | grep 8000
```

### Database Issues

```bash
# Check PostgreSQL status
docker-compose exec postgres pg_isready

# Connect to database
docker-compose exec postgres psql -U forensics forensics_db

# View connections
docker-compose exec postgres psql -U forensics -c "SELECT * FROM pg_stat_activity;"
```

### Disk Space Issues

```bash
# Check usage
df -h
du -sh /var/forensics/*

# Clean old artifacts (manual)
find /var/forensics/artifacts -mtime +30 -delete
find /var/forensics/results -mtime +30 -delete

# Clean Docker resources
docker system prune -a
docker volume prune
```

### Memory Issues

```bash
# Check resource usage
docker stats

# Reduce worker concurrency
# Edit .env: CELERY_WORKER_CONCURRENCY=1
docker-compose restart worker
```

## Maintenance Tasks

### Daily
- [ ] Check service status (`docker-compose ps`)
- [ ] Monitor disk space (`df -h`)
- [ ] Review error logs

### Weekly
- [ ] Review all logs for errors
- [ ] Check job success rate
- [ ] Monitor worker performance
- [ ] Verify backups completed

### Monthly
- [ ] Update system packages
- [ ] Review security advisories
- [ ] Rotate old artifacts
- [ ] Performance optimization
- [ ] Update documentation

## Backup & Restore

### Create Backup
```bash
# Database
docker-compose exec postgres pg_dump -U forensics forensics_db > backup_$(date +%Y%m%d).sql

# Storage
tar -czf storage_$(date +%Y%m%d).tar.gz /var/forensics/

# Configuration
cp .env .env.backup_$(date +%Y%m%d)
```

### Restore Backup
```bash
# Database
docker-compose exec -T postgres psql -U forensics forensics_db < backup_20231224.sql

# Storage
tar -xzf storage_20231224.tar.gz -C /

# Configuration
cp .env.backup_20231224 .env
docker-compose restart
```

## Configuration Changes

### Update Environment Variables
```bash
# Edit .env file
nano .env

# Apply changes
docker-compose down
docker-compose up -d
```

### Increase Upload Limit
```bash
# In .env
MAX_UPLOAD_SIZE_GB=50

# In docker/nginx.conf
client_max_body_size 50G;

# Restart
docker-compose restart nginx api
```

### Upload via URL (Recommended for Large Files)
```bash
# Instead of direct upload, queue async download (returns immediately)
curl -X POST http://localhost:8000/api/v1/upload/from-url \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/dumps/memory.raw",
    "description": "Linux server - 2025-12-24"
  }'

# Check download progress
curl http://localhost:8000/api/v1/upload/status/<image_id>

# Benefits:
# - Server downloads in background (non-blocking)
# - No browser upload limits
# - Works with S3, GCS, remote URLs
# - Memory efficient streaming
# - Progress tracking available
```

### Change Worker Concurrency
```bash
# In .env
CELERY_WORKER_CONCURRENCY=4

# Restart
docker-compose restart worker
```

## Monitoring

### Key Metrics

**API Performance**:
- Response time: < 200ms (health check)
- Upload throughput: Monitor network usage
- Error rate: < 1%

**Worker Performance**:
- Queue length: Check Flower dashboard
- Task success rate: > 95%
- Memory usage: < 80% of allocated

**Database**:
- Connection count: < 80% of pool size
- Query time: < 100ms (simple queries)
- Disk usage: < 80%

### Alerts to Configure

- Disk usage > 80%
- Worker queue length > 50
- API error rate > 5%
- Database connections > 80
- Service downtime > 5 minutes

## Performance Tuning

### Optimize Database

```sql
-- Connect to database
docker-compose exec postgres psql -U forensics forensics_db

-- Analyze tables
ANALYZE;

-- Check slow queries
SELECT query, mean_exec_time 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;

-- Create missing indexes
CREATE INDEX IF NOT EXISTS idx_jobs_status ON analysis_jobs(status);
```

### Optimize Workers

```bash
# Increase worker memory
# In docker-compose.yml under worker service:
deploy:
  resources:
    limits:
      memory: 12G
```

### Optimize Nginx

```nginx
# In docker/nginx.conf
worker_processes auto;
worker_rlimit_nofile 65535;

events {
    worker_connections 4096;
}
```

## Security Operations

### Review Access Logs

```bash
# API access
docker-compose logs api | grep "POST /api"

# Upload activity
docker-compose logs api | grep "upload"

# Authentication attempts
docker-compose logs api | grep "login"
```

### Update Secrets

```bash
# Generate new SECRET_KEY
openssl rand -hex 32

# Update .env
nano .env  # Update SECRET_KEY

# Restart (invalidates all tokens)
docker-compose restart api
```

### Check for Updates

```bash
# Update base images
docker-compose pull

# Rebuild with updates
docker-compose build --no-cache

# Restart with new images
docker-compose up -d
```

## Emergency Procedures

### Service Crash

1. Check logs: `docker-compose logs <service>`
2. Check resources: `docker stats`
3. Restart service: `docker-compose restart <service>`
4. If persists, full restart: `docker-compose down && docker-compose up -d`

### Data Corruption

1. Stop services: `docker-compose down`
2. Restore from backup
3. Verify integrity
4. Start services: `docker-compose up -d`
5. Monitor logs

### Security Incident

1. Isolate affected system
2. Preserve evidence (logs, database, storage)
3. Review access logs
4. Identify entry point
5. Patch vulnerability
6. Restore from clean backup
7. Update credentials
8. Document incident

## Useful SQL Queries

```sql
-- Connect to database
docker-compose exec postgres psql -U forensics forensics_db

-- Count jobs by status
SELECT status, COUNT(*) 
FROM analysis_jobs 
GROUP BY status;

-- Recent failed jobs
SELECT id, memory_image_id, error_message, created_at
FROM analysis_jobs
WHERE status = 'failed'
ORDER BY created_at DESC
LIMIT 10;

-- Storage by user
SELECT u.username, COUNT(m.id) as images, SUM(m.file_size_bytes)/1024/1024/1024 as size_gb
FROM users u
LEFT JOIN memory_images m ON u.id = m.uploaded_by
GROUP BY u.username;

-- Plugin success rate
SELECT plugin_name, 
       COUNT(*) as total,
       SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful,
       AVG(execution_time_seconds) as avg_time
FROM plugin_results
GROUP BY plugin_name;
```

## Contact Information

- **Emergency**: [Your on-call number]
- **Support**: [Support email]
- **Documentation**: http://localhost:8000/docs
- **Monitoring**: http://localhost:5555 (Flower)

## Quick Links

- Web UI: http://localhost
- API Docs: http://localhost:8000/docs
- Flower: http://localhost:5555
- Health: http://localhost:8000/api/v1/health
