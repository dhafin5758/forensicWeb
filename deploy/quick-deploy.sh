#!/bin/bash
# Quick deployment script - Run this on your VPS
# Usage: sudo bash quick-deploy.sh

set -e

echo "====================================="
echo "Forensics Platform - Quick Deploy"
echo "====================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run with sudo"
    exit 1
fi

# Step 1: Update system
echo "📦 [1/7] Updating system..."
apt-get update > /dev/null 2>&1
apt-get upgrade -y > /dev/null 2>&1

# Step 2: Install Docker
echo "🐳 [2/7] Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh 2>/dev/null
    bash /tmp/get-docker.sh > /dev/null 2>&1
    rm /tmp/get-docker.sh
    systemctl enable docker > /dev/null 2>&1
    systemctl start docker > /dev/null 2>&1
else
    echo "  ✓ Docker already installed"
fi

# Step 3: Install Docker Compose
echo "🐳 [3/7] Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
        -o /usr/local/bin/docker-compose 2>/dev/null
    chmod +x /usr/local/bin/docker-compose
else
    echo "  ✓ Docker Compose already installed"
fi

# Step 4: Prepare directories
echo "📁 [4/7] Creating storage directories..."
mkdir -p /var/forensics/{uploads,artifacts,results,logs}
chmod -R 755 /var/forensics

# Step 5: Configure environment
echo "⚙️  [5/7] Configuring environment..."
cd /root/forensicWeb

if [ ! -f ".env" ]; then
    cat > .env << 'EOF'
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
EOF
    # Generate actual secret key
    SECRET=$(openssl rand -hex 32)
    sed -i "s|\$(openssl rand -hex 32)|$SECRET|" .env
fi

# Step 6: Build and start
echo "🏗️  [6/7] Building containers..."
docker-compose build --quiet > /dev/null 2>&1

echo "🚀 [7/7] Starting services..."
docker-compose up -d

# Wait for services
echo ""
echo "⏳ Waiting for services to start..."
sleep 15

# Show status
echo ""
echo "====================================="
echo "✅ Deployment Complete!"
echo "====================================="
echo ""
echo "📊 Service Status:"
docker-compose ps
echo ""

# Get IP
IP=$(hostname -I | awk '{print $1}')
echo "🌐 Access your platform:"
echo "   Web UI:      http://$IP:8000"
echo "   API Docs:    http://$IP:8000/docs"
echo "   Task Monitor: http://$IP:5555"
echo ""
echo "🔐 Default credentials:"
echo "   Username: admin"
echo "   Password: password"
echo ""
echo "⚠️  IMPORTANT: Change these credentials immediately!"
echo ""
echo "❓ For help: See VPS_DEPLOYMENT_GUIDE.md"
echo "====================================="
