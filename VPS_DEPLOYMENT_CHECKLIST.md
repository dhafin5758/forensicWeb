# VPS Deployment Checklist

Use this checklist to ensure your VPS deployment is complete and working.

## 🎯 Pre-Deployment (Before VPS)

- [ ] Linux VPS provisioned (Ubuntu 20.04+, Debian 11+, etc)
- [ ] Root or sudo access verified
- [ ] VPS has 8GB+ RAM
- [ ] VPS has 100GB+ disk space
- [ ] GitHub repository URL ready
- [ ] SSH access configured

## 🚀 Automated Deployment (Fastest - 10 minutes)

```bash
cd /opt
sudo git clone https://github.com/dhafin5758/forensicWeb.git
cd forensicWeb
sudo chmod +x deploy/deploy.sh
sudo ./deploy/deploy.sh
```

- [ ] Script runs without errors
- [ ] All packages installed
- [ ] Docker containers built
- [ ] Services started

**Verify:**
```bash
docker-compose ps        # Should show 6 containers
curl http://localhost:8000/api/v1/health  # Should return 200
```

- [ ] All 6 containers running (api, worker, postgres, redis, nginx, flower)
- [ ] Health check returns JSON response
- [ ] No error messages in logs

## 📝 Manual Deployment (If Script Fails - 20 minutes)

### Phase 1: Clone & Prepare
```bash
ssh root@YOUR_VPS_IP
cd /opt
sudo git clone https://github.com/dhafin5758/forensicWeb.git forensicWeb
cd forensicWeb
```
- [ ] Repository cloned successfully
- [ ] Files present: `docker-compose.yml`, `.env.example`, `backend/`, `frontend/`, etc

### Phase 2: Install Docker
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
docker --version
```
- [ ] Docker installed (version 20.10+)
- [ ] Docker daemon running

### Phase 3: Install Docker Compose
```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
  -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
docker-compose --version
```
- [ ] Docker Compose installed (version 2.0+)

### Phase 4: Configure Environment
```bash
sudo cp .env.example .env
# Generate secrets:
openssl rand -hex 32         # SECRET_KEY
openssl rand -base64 32      # DATABASE_PASSWORD
openssl rand -base64 32      # REDIS_PASSWORD
# Edit .env with nano/vi
sudo nano .env
```
- [ ] `.env` file created
- [ ] SECRET_KEY set (32 char hex string)
- [ ] DATABASE_PASSWORD set (32 char base64 string)
- [ ] REDIS_PASSWORD set (32 char base64 string)
- [ ] UPLOAD_DIR exists: `/var/forensics/uploads`
- [ ] Storage directory created: `sudo mkdir -p /var/forensics`

### Phase 5: Build & Start Services
```bash
sudo docker-compose build      # 2-3 minutes
sudo docker-compose up -d      # Start in background
sleep 30                        # Wait for startup
sudo docker-compose logs       # Check for errors
```
- [ ] Build completes without errors
- [ ] 6 containers start successfully
- [ ] No "error" messages in logs
- [ ] All services show "running" status

## ✅ Verification (Critical - Must Pass)

### Container Status
```bash
sudo docker-compose ps
```
- [ ] `forensicweb-api-1` - running, port 8000
- [ ] `forensicweb-worker-1` - running
- [ ] `forensicweb-postgres-1` - running, port 5432
- [ ] `forensicweb-redis-1` - running, port 6379
- [ ] `forensicweb-nginx-1` - running, port 80/443
- [ ] `forensicweb-flower-1` - running, port 5555

### API Health Check
```bash
curl http://localhost:8000/api/v1/health
```
- [ ] Returns 200 status code
- [ ] Returns JSON response
- [ ] Shows service status and uptime

### Log Check
```bash
sudo docker-compose logs | head -50
```
- [ ] No "error" messages (warnings are OK)
- [ ] No "connection refused" messages
- [ ] No "permission denied" messages

### Container Logs Detail
```bash
sudo docker-compose logs api       # FastAPI startup
sudo docker-compose logs worker    # Celery worker ready
sudo docker-compose logs postgres  # Database connection
```
- [ ] API logs show "Application startup complete"
- [ ] Worker logs show "ready to accept tasks"
- [ ] Postgres logs show "database system is ready"

## 🌐 Web Access (Verify UI)

### Check All Access Points
```bash
# Replace YOUR_VPS_IP with your actual VPS IP
curl http://YOUR_VPS_IP:8000/
curl http://YOUR_VPS_IP:8000/docs
curl http://YOUR_VPS_IP:5555/
```
- [ ] Main UI responds (port 8000)
- [ ] API documentation available (port 8000/docs)
- [ ] Flower dashboard available (port 5555)

### Browser Access
- [ ] Open `http://YOUR_VPS_IP:8000` in browser
- [ ] Web UI loads with "Volatility 3 Memory Forensics Platform" title
- [ ] Dashboard shows system status
- [ ] "Upload Memory Image" section visible
- [ ] "Download from URL" section visible

## 🔐 Security (Post-Deployment)

### Firewall Setup
```bash
sudo ufw enable
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw default deny incoming
sudo ufw status
```
- [ ] UFW enabled
- [ ] SSH (22) allowed
- [ ] HTTP (80) allowed
- [ ] HTTPS (443) allowed

### Change Default Credentials
```bash
# Access API to change admin password
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"newadmin","password":"secure_password","email":"admin@example.com"}'
```
- [ ] Created new admin user with strong password
- [ ] Changed default credentials

### Backup Secrets
```bash
sudo cp .env .env.backup
sudo chmod 600 .env .env.backup
```
- [ ] `.env` backup created
- [ ] Permissions set to 600 (owner only)

## 📊 Functionality Tests

### Upload Test
```bash
# Create a small test file
dd if=/dev/zero of=test_dump.raw bs=1M count=10

# Upload via curl (need JWT token first)
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}' | jq -r '.access_token')

curl -X POST http://localhost:8000/api/v1/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test_dump.raw"
```
- [ ] Upload endpoint responds
- [ ] Returns image_id in response
- [ ] File saved to `/var/forensics/uploads/`

### URL Download Test
```bash
# Test with a publicly accessible small file
curl -X POST http://localhost:8000/api/v1/upload/from-url \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"url":"https://example.com/test_file.raw"}'
```
- [ ] Endpoint accepts request
- [ ] Returns 202 Accepted
- [ ] Returns image_id
- [ ] Task queued in Flower dashboard

### Database Test
```bash
sudo docker-compose exec postgres psql -U forensics -d forensics_db -c "SELECT version();"
```
- [ ] PostgreSQL responds
- [ ] Database is accessible
- [ ] Version information returns

### Redis Test
```bash
sudo docker-compose exec redis redis-cli ping
```
- [ ] Redis responds with "PONG"
- [ ] Cache is accessible

## 📈 Performance Baseline

```bash
# Check initial resource usage
docker stats
df -h
free -h
```
- [ ] CPU usage reasonable (< 50% idle)
- [ ] Memory usage acceptable (< 5GB of 8GB)
- [ ] Disk has space (100GB+ available)
- [ ] Network connectivity good

## 📝 Documentation & Notes

- [ ] Read [VPS_DEPLOYMENT_GUIDE.md](VPS_DEPLOYMENT_GUIDE.md)
- [ ] Read [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- [ ] Reviewed [docs/URL_DOWNLOAD.md](docs/URL_DOWNLOAD.md) for usage
- [ ] Reviewed [docs/API_GUIDE.md](docs/API_GUIDE.md) for API reference

## 🎓 First Run

### Via Web UI
- [ ] Navigate to `http://YOUR_VPS_IP:8000`
- [ ] Upload or URL-download a test memory image
- [ ] Create analysis job
- [ ] Wait for completion
- [ ] View results

### Via CLI
- [ ] Test curl with authentication
- [ ] Queue a URL download
- [ ] Check status
- [ ] Create analysis job
- [ ] Retrieve results

### Via Bash Script
- [ ] Run `bash examples/download_from_url.sh`
- [ ] Follow interactive prompts
- [ ] Verify workflow completes

## 🚨 Emergency Procedures

### If Services Stop
```bash
sudo docker-compose restart
```
- [ ] Services restart successfully
- [ ] Health check passes after restart

### If Database Corrupt
```bash
sudo docker-compose down
sudo docker-compose up -d
```
- [ ] Services recover
- [ ] Database reinitializes

### If Disk Full
```bash
df -h
du -sh /var/forensics/*
# Remove old artifacts if needed
```
- [ ] Free up disk space
- [ ] Services recover

### If Need to Reset Everything
```bash
sudo docker-compose down
sudo docker-compose build --no-cache
sudo docker-compose up -d
```
- [ ] Complete reset successful
- [ ] Services operational

## 📊 Monitoring Setup (Optional)

```bash
# Monitor logs in real-time
watch -n 1 'docker-compose ps'

# Or use Flower dashboard
# http://YOUR_VPS_IP:5555
```
- [ ] Set up log rotation (optional)
- [ ] Set up backup schedule (optional)
- [ ] Configure monitoring alerts (optional)

## 🎉 Final Checklist

- [ ] All containers running
- [ ] API health check passes
- [ ] Web UI accessible
- [ ] Upload/download functional
- [ ] Database connected
- [ ] Redis cache working
- [ ] Firewall configured
- [ ] Credentials secured
- [ ] Documentation reviewed
- [ ] Backups configured

## 📞 If Something Fails

| Problem | Solution | Docs |
|---------|----------|------|
| Docker not found | Reinstall from `get-docker.sh` | [VPS_DEPLOYMENT_GUIDE.md](VPS_DEPLOYMENT_GUIDE.md) |
| Port 8000 in use | Change port in `docker-compose.yml` | [VPS_DEPLOYMENT_GUIDE.md](VPS_DEPLOYMENT_GUIDE.md) |
| API not responding | Check logs: `docker-compose logs api` | [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) |
| Database error | Check logs: `docker-compose logs postgres` | [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) |
| Worker not running | Restart: `docker-compose restart worker` | [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) |

---

## 🎊 Success Indicators

If all of the following are true, your deployment is successful:

✅ All 6 containers running  
✅ API health check returns 200  
✅ Web UI loads in browser  
✅ Database is connected  
✅ Redis cache is accessible  
✅ Upload endpoint functional  
✅ URL download endpoint functional  
✅ Flower dashboard accessible  
✅ No error messages in logs  
✅ Resources within acceptable limits  

**Congratulations! Your Volatility 3 Memory Forensics Platform is fully deployed and operational!** 🚀

---

## Next Steps

1. **Read Documentation**
   - [VPS_DEPLOYMENT_GUIDE.md](VPS_DEPLOYMENT_GUIDE.md) - Complete deployment guide
   - [docs/URL_DOWNLOAD.md](docs/URL_DOWNLOAD.md) - Using URL download feature
   - [docs/API_GUIDE.md](docs/API_GUIDE.md) - API reference

2. **Test the System**
   - Upload a small test memory image
   - Try URL download feature
   - Create analysis job
   - View results

3. **Configure for Production**
   - Set up SSL/TLS certificates
   - Configure backup procedures
   - Set up monitoring
   - Configure log rotation

4. **Start Using**
   - Add real memory images for analysis
   - Automate workflows
   - Monitor system health
   - Review results

---

*Deployment Date: _______________*  
*VPS IP: _______________*  
*Admin User Created: _______________*  
*Notes: _____________________________________________*
