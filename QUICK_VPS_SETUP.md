# VPS Deployment - One Command Quick Start

## 🚀 Fastest Way (Copy & Paste)

### Option 1: Automated (Recommended)

```bash
cd /opt && \
sudo git clone https://github.com/dhafin5758/forensicWeb.git && \
cd forensicWeb && \
sudo chmod +x deploy/deploy.sh && \
sudo ./deploy/deploy.sh
```

Then visit: **`http://YOUR_VPS_IP:8000`**

---

### Option 2: Manual (Step by Step)

```bash
# Step 1: SSH in and prepare
ssh root@YOUR_VPS_IP
cd /opt
sudo git clone https://github.com/dhafin5758/forensicWeb.git forensicWeb
cd forensicWeb

# Step 2: Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh && rm get-docker.sh

# Step 3: Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
  -o /usr/local/bin/docker-compose && sudo chmod +x /usr/local/bin/docker-compose

# Step 4: Setup environment
sudo cp .env.example .env
sudo mkdir -p /var/forensics/uploads /var/forensics/artifacts /var/forensics/results

# Step 5: Edit .env (change passwords)
sudo nano .env

# Step 6: Build and start
sudo docker-compose build && sudo docker-compose up -d

# Step 7: Verify (wait 30 seconds first)
sleep 30
docker-compose ps
curl http://localhost:8000/api/v1/health
```

Then visit: **`http://YOUR_VPS_IP:8000`**

---

## ✅ Verification (Copy & Paste)

```bash
# All containers running?
docker-compose ps

# API healthy?
curl http://localhost:8000/api/v1/health

# View logs
docker-compose logs --tail=20

# Open in browser
echo "Visit: http://$(hostname -I | awk '{print $1}'):8000"
```

---

## 🆘 Troubleshooting (Copy & Paste)

```bash
# Check what's wrong
docker-compose logs api      # API errors?
docker-compose logs worker   # Worker errors?
docker-compose logs postgres # Database errors?

# Restart everything
docker-compose restart

# Full reset
docker-compose down && docker-compose up -d

# Check resources
docker stats

# Check disk
df -h /var/forensics
```

---

## 🔐 Secure It (Copy & Paste)

```bash
# Enable firewall
sudo ufw enable
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw default deny incoming
sudo ufw status

# Backup config
sudo cp .env .env.backup && sudo chmod 600 .env .env.backup
```

---

## 📊 Monitor It (Copy & Paste)

```bash
# Watch containers in real-time
watch docker-compose ps

# View resource usage
docker stats

# Follow logs
docker-compose logs -f

# Task queue dashboard
echo "Visit: http://$(hostname -I | awk '{print $1}'):5555"
```

---

## 🎯 Test It (Copy & Paste)

```bash
# Get token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}' | jq -r '.access_token')

# Test URL download
curl -X POST http://localhost:8000/api/v1/upload/from-url \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/test.raw","description":"test"}'

# Check Flower dashboard for task
echo "Visit: http://$(hostname -I | awk '{print $1}'):5555"
```

---

## 📍 Access Points (Copy & Paste)

```bash
# Get your VPS IP
YOUR_IP=$(hostname -I | awk '{print $1}')

# Print all access points
echo "🌐 Web UI:      http://$YOUR_IP:8000"
echo "📚 API Docs:    http://$YOUR_IP:8000/docs"
echo "📊 Task Monitor: http://$YOUR_IP:5555"
```

---

## 📚 Read These Next

- **[VPS_DEPLOYMENT_GUIDE.md](VPS_DEPLOYMENT_GUIDE.md)** - Complete guide (20 min read)
- **[VPS_DEPLOYMENT_CHECKLIST.md](VPS_DEPLOYMENT_CHECKLIST.md)** - Verification checklist
- **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Advanced deployment options
- **[docs/URL_DOWNLOAD.md](docs/URL_DOWNLOAD.md)** - How to use the platform

---

## 🎊 That's It!

Your Volatility 3 Memory Forensics Platform is running. Visit **`http://YOUR_VPS_IP:8000`** and start analyzing memory dumps!

---

## 💾 Backup Commands (Copy & Paste)

```bash
# Daily backup
sudo docker-compose exec postgres pg_dump -U forensics forensics_db > daily_backup_$(date +%Y-%m-%d).sql

# Backup .env
sudo cp .env .env.backup_$(date +%Y-%m-%d)

# Backup everything
sudo tar -czf forensic_platform_backup_$(date +%Y-%m-%d).tar.gz /var/forensics/ .env
```

---

## 🔄 Update Commands (Copy & Paste)

```bash
# Update from GitHub
cd /opt/forensicWeb
git pull

# Rebuild containers
docker-compose down
docker-compose pull
docker-compose build
docker-compose up -d
```

---

## ⚠️ Emergency Reset (Copy & Paste)

```bash
# CAUTION: This removes everything
docker-compose down -v
docker system prune -a --volumes
rm -rf /var/forensics/*

# Redeploy from scratch
sudo docker-compose build
sudo docker-compose up -d
```

---

**Questions?** See [VPS_DEPLOYMENT_GUIDE.md](VPS_DEPLOYMENT_GUIDE.md)
