#!/bin/bash
# Manual deployment - Copy and paste commands one by one

echo "=== Manual VPS Deployment Steps ==="
echo ""
echo "Copy each command below and paste into your VPS terminal"
echo ""

cat << 'EOF'
# ===== STEP 1: Update System =====
sudo apt-get update
sudo apt-get upgrade -y

# ===== STEP 2: Install Docker =====
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
rm get-docker.sh
sudo systemctl enable docker
sudo systemctl start docker

# ===== STEP 3: Install Docker Compose =====
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
  -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# ===== STEP 4: Clone Repository =====
cd /root
git clone https://github.com/dhafin5758/forensicWeb.git
cd forensicWeb

# ===== STEP 5: Create Directories =====
sudo mkdir -p /var/forensics/{uploads,artifacts,results,logs}
sudo chmod -R 755 /var/forensics

# ===== STEP 6: Create .env File =====
cat > .env << 'ENVEOF'
DEBUG=false
ENVIRONMENT=production
SECRET_KEY=$(openssl rand -hex 32)
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
ALLOWED_ORIGINS=["http://localhost:3000"]
STORAGE_ROOT=/var/forensics
MAX_UPLOAD_SIZE_GB=20
DATABASE_URL=postgresql+asyncpg://forensics:forensics_secure_password@postgres/forensics_db
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
CELERY_WORKER_CONCURRENCY=2
VOL3_PATH=/usr/local/bin/vol
BINWALK_PATH=/usr/bin/binwalk
EXIFTOOL_PATH=/usr/bin/exiftool
UPLOAD_TIMEOUT_SECONDS=3600
ENVEOF

# Generate real secret key
SECRET=$(openssl rand -hex 32)
sed -i "s|\$(openssl rand -hex 32)|$SECRET|" .env

# ===== STEP 7: Build Containers =====
sudo docker-compose build

# ===== STEP 8: Start Services =====
sudo docker-compose up -d

# ===== STEP 9: Wait and Check =====
sleep 15
docker-compose ps
curl http://localhost:8000/api/v1/health

# ===== STEP 10: Get Your IP =====
echo "Your platform is at: http://$(hostname -I | awk '{print $1}'):8000"

EOF

echo ""
echo "Documentation:"
echo "  - Full guide: cat VPS_DEPLOYMENT_GUIDE.md"
echo "  - Checklist: cat VPS_DEPLOYMENT_CHECKLIST.md"
echo "  - Quick ref: cat QUICK_VPS_SETUP.md"
