# VPS Deployment Guide - From Zero to Running

**Goal:** Deploy Volatility 3 Memory Forensics Platform from GitHub onto a Linux VPS  
**Time:** ~30 minutes  
**Difficulty:** Easy (automated script included)

---

## 📋 Prerequisites Checklist

Before you start, you need:

- ✅ Linux VPS (Ubuntu 20.04+ or Debian 11+)
- ✅ Root or sudo access
- ✅ Minimum 8GB RAM
- ✅ 100GB+ disk space
- ✅ GitHub repository cloned or ready to clone
- ✅ Internet access (for downloading Docker, packages)

---

## 🚀 Fastest Deployment (10 minutes)

### Step 1: SSH into Your VPS

```bash
ssh root@your.vps.ip.address
# Or: ssh -i /path/to/key.pem ubuntu@your.vps.ip.address
```

### Step 2: Clone Repository

```bash
cd /opt
sudo git clone https://github.com/dhafin5758/forensicWeb.git
cd forensicWeb
```

### Step 3: Run Automated Deployment Script

```bash
sudo chmod +x deploy/deploy.sh
sudo ./deploy/deploy.sh
```

The script automatically:
- Installs Docker & Docker Compose
- Installs all dependencies
- Builds containers
- Configures environment
- Starts all services

### Step 4: Verify It's Running

```bash
# Check services (should show 6 containers running)
docker-compose ps

# Test API (should return 200)
curl http://localhost:8000/api/v1/health

# View logs (should be running without errors)
docker-compose logs --tail=20
```

### Step 5: Access the Application

Open your browser:
```
http://YOUR_VPS_IP:8000
```

✅ **Done!** Your platform is live.

---

## 📝 Step-by-Step Manual Deployment

If you prefer to do it manually or the script fails:

### Phase 1: System Preparation (5 minutes)

```bash
# 1. SSH into VPS
ssh root@your.vps.ip.address

# 2. Update system packages
sudo apt-get update
sudo apt-get upgrade -y

# 3. Create application directory
sudo mkdir -p /opt/forensics-platform
cd /opt/forensics-platform

# 4. Clone the repository
sudo git clone https://github.com/dhafin5758/forensicWeb.git .
```

### Phase 2: Install Docker (3 minutes)

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
rm get-docker.sh

# Allow current user to use Docker (optional)
sudo usermod -aG docker $USER
newgrp docker

# Verify Docker installed
docker --version
```

### Phase 3: Install Docker Compose (2 minutes)

```bash
# Download Docker Compose (latest)
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
  -o /usr/local/bin/docker-compose

# Make executable
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker-compose --version
```

### Phase 4: Configure Environment (3 minutes)

```bash
# Copy environment template
sudo cp .env.example .env

# Edit configuration (use nano or your preferred editor)
sudo nano .env

# Required changes:
# 1. Leave most defaults (they're optimized)
# 2. Update these if needed:
#    - DATABASE_PASSWORD (change to something secure)
#    - REDIS_PASSWORD (change to something secure)
#    - SECRET_KEY (see Step 5 below)
```

**Generate Secure Secrets:**

```bash
# Generate SECRET_KEY (32 random hex characters)
openssl rand -hex 32

# Copy output and paste into .env for SECRET_KEY

# Generate DATABASE_PASSWORD
openssl rand -base64 32

# Copy output and paste into .env for DATABASE_PASSWORD

# Generate REDIS_PASSWORD
openssl rand -base64 32

# Copy output and paste into .env for REDIS_PASSWORD
```

### Phase 5: Build and Start Services (5 minutes)

```bash
# Navigate to project directory
cd /opt/forensics-platform

# Build Docker images (first time only, ~2 minutes)
sudo docker-compose build

# Start all services in background
sudo docker-compose up -d

# Watch startup logs (press Ctrl+C to exit)
sudo docker-compose logs -f

# Wait for services to be ready (~30 seconds)
# You should see:
# - api_1 ready
# - worker_1 ready  
# - nginx_1 ready
```

### Phase 6: Verify Everything Works

```bash
# Check all containers are running
sudo docker-compose ps
# You should see 6 containers: api, worker, postgres, redis, nginx, flower

# Test API health
curl http://localhost:8000/api/v1/health
# Should return JSON with status

# Check logs for errors
sudo docker-compose logs | grep -i error
# Should be empty or minimal

# View specific service logs
sudo docker-compose logs api      # FastAPI server
sudo docker-compose logs worker   # Celery workers
sudo docker-compose logs postgres # Database
```

### Phase 7: Access the Application

**Web Interface:**
```
http://YOUR_VPS_IP:8000
```

**API Documentation:**
```
http://YOUR_VPS_IP:8000/docs
```

**Flower (Task Queue Monitor):**
```
http://YOUR_VPS_IP:5555
```

---

## 🔐 Security Configuration (Post-Deployment)

After everything is running, configure security:

### 1. Set Up Firewall

```bash
# Enable UFW (Ubuntu Firewall)
sudo ufw enable

# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP
sudo ufw allow 80/tcp

# Allow HTTPS (when you add SSL)
sudo ufw allow 443/tcp

# Close everything else
sudo ufw default deny incoming

# Check status
sudo ufw status
```

### 2. Set Up SSL/TLS (Let's Encrypt)

```bash
# Install Certbot
sudo apt-get install certbot python3-certbot-nginx -y

# Get certificate (replace with your domain)
sudo certbot certonly --standalone -d your.domain.com

# Update docker-compose.yml to use SSL
# Edit nginx.conf to redirect HTTP → HTTPS
```

### 3. Configure Nginx Reverse Proxy

The setup already includes Nginx, but you can:

```bash
# View Nginx config
sudo cat docker/nginx.conf

# Test config
sudo docker-compose exec nginx nginx -t

# Reload Nginx
sudo docker-compose exec nginx nginx -s reload
```

---

## 📊 Post-Deployment Checklist

Verify everything works:

- ✅ All containers running: `docker-compose ps`
- ✅ API responsive: `curl http://localhost:8000/api/v1/health`
- ✅ Web UI loads: `http://YOUR_VPS_IP:8000`
- ✅ API docs work: `http://YOUR_VPS_IP:8000/docs`
- ✅ Database connected: Check logs for no errors
- ✅ Workers ready: `docker-compose logs worker | grep ready`
- ✅ Flower dashboard: `http://YOUR_VPS_IP:5555`

---

## 🛠️ Common Post-Deployment Tasks

### View Real-Time Logs

```bash
# All services
sudo docker-compose logs -f

# Specific service
sudo docker-compose logs -f api
sudo docker-compose logs -f worker

# Search logs
sudo docker-compose logs | grep "error"
```

### Restart Services

```bash
# Restart everything
sudo docker-compose restart

# Restart specific service
sudo docker-compose restart api
sudo docker-compose restart worker

# Rebuild and restart
sudo docker-compose down
sudo docker-compose build
sudo docker-compose up -d
```

### Check Resource Usage

```bash
# Container resource usage
sudo docker stats

# Disk usage
df -h
du -sh /var/forensics/

# Memory usage
free -h

# CPU usage
top
```

### Database Management

```bash
# Access PostgreSQL
sudo docker-compose exec postgres psql -U forensics

# Inside psql:
# \dt                    (list tables)
# \l                     (list databases)
# SELECT * FROM users;   (query data)
# \q                     (exit)
```

### Backup Data

```bash
# Backup PostgreSQL database
sudo docker-compose exec postgres pg_dump -U forensics forensics_db > backup.sql

# Backup uploaded files
sudo tar -czf artifacts_backup.tar.gz /var/forensics/

# Backup entire environment
sudo docker-compose exec api cat .env > .env.backup
```

---

## 🆘 Troubleshooting

### "Docker not found"

```bash
# Reinstall Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### "Port 8000 already in use"

```bash
# Find process using port 8000
sudo lsof -i :8000

# Kill the process (if safe)
sudo kill -9 <PID>

# Or change port in docker-compose.yml
```

### "API not responding"

```bash
# Check if container is running
docker-compose ps api

# View error logs
docker-compose logs api

# Restart API service
docker-compose restart api

# Check resource limits
docker stats api
```

### "Database connection failed"

```bash
# Check PostgreSQL container
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs postgres

# Check database exists
docker-compose exec postgres psql -U forensics -l

# Restart database
docker-compose restart postgres
```

### "Workers not processing tasks"

```bash
# Check worker container
docker-compose ps worker

# View worker logs
docker-compose logs worker

# Check task queue (Flower)
# Go to http://localhost:5555

# Restart workers
docker-compose restart worker
```

### "Out of disk space"

```bash
# Check disk usage
df -h

# Find large files
du -sh /var/forensics/*

# Clean old uploads (if safe)
sudo rm -rf /var/forensics/uploads/*.tmp

# Clean Docker images
docker image prune -a
docker container prune
docker system prune -a
```

---

## 📈 Monitoring & Maintenance

### Daily Tasks

```bash
# Check system health
docker-compose ps
docker-compose logs --tail=20

# Monitor resources
docker stats
```

### Weekly Tasks

```bash
# Check for updates
git pull
docker-compose pull

# Backup database
docker-compose exec postgres pg_dump -U forensics forensics_db > weekly_backup.sql

# Review logs for errors
docker-compose logs | grep error
```

### Monthly Tasks

```bash
# Update all images
docker-compose down
docker-compose pull
docker-compose up -d

# Clean up old data
docker system prune

# Verify backups are working
ls -la *_backup.sql
```

---

## 🎯 Using the Platform

Once running, here's how to use it:

### Via Web UI

1. Go to `http://YOUR_VPS_IP:8000`
2. Click "Download from URL" or "Upload"
3. Provide file/URL
4. Click "Queue Download" or upload
5. Monitor progress in dashboard
6. View results when complete

### Via Command Line

```bash
# Get your JWT token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}' | jq -r '.access_token')

# Queue URL download
curl -X POST http://localhost:8000/api/v1/upload/from-url \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"url":"https://example.com/memory.raw"}'

# Check status
curl http://localhost:8000/api/v1/upload/status/<image_id>

# Create analysis job
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"memory_image_id":"<image_id>","plugins":["pslist","pstree"]}'
```

### Via Bash Script

```bash
# Use provided example script
bash examples/download_from_url.sh
```

---

## 📚 Important Files & Locations

| Location | Purpose |
|----------|---------|
| `/opt/forensics-platform` | Application root |
| `/opt/forensics-platform/.env` | Configuration |
| `/var/forensics/uploads/` | Uploaded memory images |
| `/var/forensics/artifacts/` | Extracted artifacts |
| `/var/forensics/results/` | Analysis results |
| `/var/lib/docker/volumes/` | Docker data (DB, Redis) |

---

## 🔑 Credentials

After deployment, use these default credentials:

| Service | Username | Default Password |
|---------|----------|------------------|
| Web UI | `admin` | Check logs (generated) |
| Database | `forensics` | Set in .env |
| Redis | - | Set in .env |

**Important:** Change all default passwords immediately!

---

## 📞 Support & Next Steps

### For Issues
1. Check logs: `docker-compose logs`
2. Review [docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md)
3. Check [docs/TROUBLESHOOTING.md](../docs/TROUBLESHOOTING.md) (if exists)

### For Learning
1. Read [docs/URL_DOWNLOAD.md](../docs/URL_DOWNLOAD.md)
2. Review [docs/API_GUIDE.md](../docs/API_GUIDE.md)
3. Try examples in [examples/](../examples/)

### For Features
1. Check web UI at `http://YOUR_VPS_IP:8000`
2. API docs at `http://YOUR_VPS_IP:8000/docs`
3. Task queue at `http://YOUR_VPS_IP:5555` (Flower)

---

## ✅ Deployment Complete!

Your Volatility 3 Memory Forensics Platform is now:
- ✅ Running on your VPS
- ✅ Accessible from the web
- ✅ Processing forensic analysis
- ✅ Ready for production use

**Congratulations! 🎉**

---

## Quick Reference

### Essential Commands

```bash
# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Restart everything
docker-compose restart

# Stop all services
docker-compose stop

# Start all services
docker-compose up -d

# Update from GitHub
git pull
docker-compose pull
docker-compose restart

# Full rebuild
docker-compose down
docker-compose build
docker-compose up -d
```

### Access Points

```
Web UI:        http://YOUR_VPS_IP:8000
API Docs:      http://YOUR_VPS_IP:8000/docs
Task Monitor:  http://YOUR_VPS_IP:5555 (Flower)
```

---

*For detailed deployment information, see [docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md)*  
*For troubleshooting, check [TROUBLESHOOTING.md](../TROUBLESHOOTING.md)*  
*For usage, see [URL_DOWNLOAD.md](../docs/URL_DOWNLOAD.md) or [API_GUIDE.md](../docs/API_GUIDE.md)*
