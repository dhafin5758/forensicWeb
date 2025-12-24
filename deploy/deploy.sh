#!/bin/bash
# Deployment script for Volatility 3 Forensics Platform

set -e

echo "====================================="
echo "Forensics Platform Deployment"
echo "====================================="

# Check if running as root (needed for some operations)
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root or with sudo"
    exit 1
fi

# Update system
echo "[1/8] Updating system packages..."
apt-get update && apt-get upgrade -y

# Install Docker and Docker Compose
echo "[2/8] Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    systemctl enable docker
    systemctl start docker
else
    echo "Docker already installed"
fi

if ! command -v docker-compose &> /dev/null; then
    echo "Installing Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
else
    echo "Docker Compose already installed"
fi

# Install system dependencies
echo "[3/8] Installing system dependencies..."
apt-get install -y \
    python3 \
    python3-pip \
    git \
    build-essential \
    postgresql-client \
    redis-tools

# Create application directory
echo "[4/8] Setting up application directory..."
APP_DIR="/opt/forensics-platform"
mkdir -p $APP_DIR
cd $APP_DIR

# Clone or update repository
if [ -d ".git" ]; then
    echo "Updating existing installation..."
    git pull
else
    echo "This script assumes code is already in place"
fi

# Create environment file
echo "[5/8] Configuring environment..."
if [ ! -f ".env" ]; then
    # Create .env.example if it doesn't exist
    if [ ! -f ".env.example" ]; then
        cat > .env.example << 'EOF'
# Environment Configuration for Forensics Platform
DEBUG=false
ENVIRONMENT=production
SECRET_KEY=CHANGE_THIS_TO_A_SECURE_RANDOM_STRING_AT_LEAST_32_CHARS
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
ALLOWED_ORIGINS=["http://localhost:3000","https://yourdomain.com"]
STORAGE_ROOT=/var/forensics
MAX_UPLOAD_SIZE_GB=20
DATABASE_URL=postgresql+asyncpg://forensics:CHANGE_THIS_PASSWORD@postgres/forensics_db
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
CELERY_WORKER_CONCURRENCY=2
VOL3_PATH=/usr/local/bin/vol
BINWALK_PATH=/usr/bin/binwalk
EXIFTOOL_PATH=/usr/bin/exiftool
UPLOAD_TIMEOUT_SECONDS=3600
EOF
    fi
    cp .env.example .env
    
    # Generate secure secret key
    SECRET_KEY=$(openssl rand -hex 32)
    sed -i "s/CHANGE_THIS_TO_A_SECURE_RANDOM_STRING_AT_LEAST_32_CHARS/$SECRET_KEY/" .env
    
    # Generate database password
    DB_PASSWORD=$(openssl rand -hex 16)
    sed -i "s/CHANGE_THIS_PASSWORD/$DB_PASSWORD/" .env
    
    # Update docker-compose.yml with the password
    sed -i "s/forensics_secure_password/$DB_PASSWORD/" docker-compose.yml
    
    echo "Environment file created. Please review .env and update as needed."
else
    echo "Environment file already exists"
fi

# Create storage directories
echo "[6/8] Creating storage directories..."
mkdir -p /var/forensics/{uploads,artifacts,results,logs}
chmod -R 750 /var/forensics

# Build and start containers
echo "[7/8] Building Docker containers..."
docker-compose build

echo "[8/8] Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 10

# Check service health
echo ""
echo "====================================="
echo "Checking service health..."
echo "====================================="

docker-compose ps

echo ""
echo "Testing API endpoint..."
curl -s http://localhost:8000/api/v1/health | python3 -m json.tool || echo "API not yet ready"

echo ""
echo "====================================="
echo "Deployment Complete!"
echo "====================================="
echo ""
echo "Access the platform:"
echo "  - Web UI: http://$(hostname -I | awk '{print $1}')"
echo "  - API Docs: http://$(hostname -I | awk '{print $1}')/docs"
echo "  - Flower (Celery): http://$(hostname -I | awk '{print $1}'):5555"
echo ""
echo "Useful commands:"
echo "  - View logs: docker-compose logs -f"
echo "  - Stop services: docker-compose down"
echo "  - Restart: docker-compose restart"
echo ""
echo "IMPORTANT: Update .env file with production settings!"
echo "====================================="
