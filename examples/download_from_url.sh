#!/bin/bash
# Download memory image from URL and start analysis
# Ideal for: Large files, remote URLs, automated pipelines

set -e

# Configuration
API_BASE="http://localhost:8000/api/v1"
TOKEN="YOUR_JWT_TOKEN_HERE"  # Replace with actual token
DOWNLOAD_URL="https://example.com/dumps/memory.raw"
DESCRIPTION="Automated download - $(date +%Y-%m-%d\ %H:%M:%S)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Forensics Platform - URL Download ===${NC}\n"

# Validate token
if [ "$TOKEN" == "YOUR_JWT_TOKEN_HERE" ]; then
    echo -e "${RED}ERROR: Please set TOKEN variable with your actual JWT token${NC}"
    exit 1
fi

# Validate URL
if [ "$DOWNLOAD_URL" == "https://example.com/dumps/memory.raw" ]; then
    echo -e "${RED}ERROR: Please set DOWNLOAD_URL to an actual download link${NC}"
    exit 1
fi

echo -e "${YELLOW}Downloading from:${NC} $DOWNLOAD_URL"
echo -e "${YELLOW}Description:${NC} $DESCRIPTION\n"

# Step 1: Queue download
echo -e "${BLUE}[1/3] Queuing download...${NC}"

RESPONSE=$(curl -s -X POST "$API_BASE/upload/from-url" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
        \"url\": \"$DOWNLOAD_URL\",
        \"description\": \"$DESCRIPTION\"
    }")

# Extract image_id from response
IMAGE_ID=$(echo "$RESPONSE" | grep -o '"image_id":"[^"]*' | cut -d'"' -f4)

if [ -z "$IMAGE_ID" ]; then
    echo -e "${RED}ERROR: Failed to queue download${NC}"
    echo "Response: $RESPONSE"
    exit 1
fi

echo -e "${GREEN}✓ Download queued${NC}"
echo -e "  Image ID: ${BLUE}$IMAGE_ID${NC}\n"

# Step 2: Monitor download progress
echo -e "${BLUE}[2/3] Monitoring download progress...${NC}"

max_attempts=360  # 1 hour (10 second intervals)
attempt=0
completed=false

while [ $attempt -lt $max_attempts ]; do
    STATUS=$(curl -s -H "Authorization: Bearer $TOKEN" \
        "$API_BASE/upload/status/$IMAGE_ID")
    
    STATE=$(echo "$STATUS" | grep -o '"status":"[^"]*' | cut -d'"' -f4)
    
    case "$STATE" in
        "completed")
            FILE_SIZE=$(echo "$STATUS" | grep -o '"file_size_bytes":[0-9]*' | cut -d':' -f2)
            SHA256=$(echo "$STATUS" | grep -o '"file_hash_sha256":"[^"]*' | cut -d'"' -f4)
            
            SIZE_GB=$(echo "scale=2; $FILE_SIZE / 1024 / 1024 / 1024" | bc)
            
            echo -e "\r${GREEN}✓ Download complete!${NC}                    "
            echo -e "  File size: ${BLUE}${SIZE_GB} GB${NC}"
            echo -e "  SHA256: ${BLUE}${SHA256}${NC}\n"
            completed=true
            break
            ;;
        "downloading")
            PERCENT=$(echo "$STATUS" | grep -o '"percent_complete":[0-9]*' | cut -d':' -f2)
            printf "\r  ⏳ Download progress: ${BLUE}${PERCENT}%%${NC}         "
            ;;
        "error")
            ERROR=$(echo "$STATUS" | grep -o '"error":"[^"]*' | cut -d'"' -f4)
            echo -e "\r${RED}✗ Download failed: $ERROR${NC}                "
            exit 1
            ;;
        *)
            printf "\r  ⏳ Waiting (attempt $((attempt+1))/$max_attempts)...    "
            ;;
    esac
    
    sleep 10
    attempt=$((attempt + 1))
done

if [ "$completed" = false ]; then
    echo -e "\n${RED}ERROR: Download timeout (60 minutes exceeded)${NC}"
    exit 1
fi

# Step 3: Create analysis job
echo -e "${BLUE}[3/3] Starting analysis job...${NC}"

JOB_RESPONSE=$(curl -s -X POST "$API_BASE/jobs/" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
        \"memory_image_id\": \"$IMAGE_ID\",
        \"plugins\": [\"pslist\", \"pstree\", \"netscan\", \"cmdline\", \"malfind\", \"filescan\"],
        \"priority\": 8
    }")

JOB_ID=$(echo "$JOB_RESPONSE" | grep -o '"id":"[^"]*' | cut -d'"' -f4)

if [ -z "$JOB_ID" ]; then
    echo -e "${RED}ERROR: Failed to create analysis job${NC}"
    echo "Response: $JOB_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✓ Analysis started${NC}"
echo -e "  Job ID: ${BLUE}$JOB_ID${NC}\n"

# Summary
echo -e "${GREEN}=== Success ===${NC}"
echo -e "Image ID:   ${BLUE}$IMAGE_ID${NC}"
echo -e "Job ID:     ${BLUE}$JOB_ID${NC}"
echo -e "Size:       ${BLUE}${SIZE_GB} GB${NC}"
echo -e "SHA256:     ${BLUE}${SHA256}${NC}\n"

echo -e "${YELLOW}Next steps:${NC}"
echo -e "  • Check job status: ${BLUE}curl -H \"Authorization: Bearer \$TOKEN\" $API_BASE/jobs/$JOB_ID${NC}"
echo -e "  • Get results:      ${BLUE}curl -H \"Authorization: Bearer \$TOKEN\" $API_BASE/results/$JOB_ID${NC}"
echo -e "  • View dashboard:   ${BLUE}http://localhost:8000${NC}\n"

# Optional: Monitor job until complete
read -p "Monitor job until complete? (y/n) " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "\n${BLUE}Monitoring job progress...${NC}"
    
    while true; do
        JOB_STATUS=$(curl -s -H "Authorization: Bearer $TOKEN" \
            "$API_BASE/jobs/$JOB_ID")
        
        STATUS=$(echo "$JOB_STATUS" | grep -o '"status":"[^"]*' | cut -d'"' -f4)
        COMPLETED=$(echo "$JOB_STATUS" | grep -o '"completed_plugins":[0-9]*' | cut -d':' -f2)
        TOTAL=$(echo "$JOB_STATUS" | grep -o '"total_plugins":[0-9]*' | cut -d':' -f2)
        
        if [ -n "$COMPLETED" ] && [ -n "$TOTAL" ] && [ "$TOTAL" != "0" ]; then
            PERCENT=$((COMPLETED * 100 / TOTAL))
            printf "\r${YELLOW}Status:${NC} $STATUS | ${BLUE}$COMPLETED/$TOTAL${NC} plugins (${BLUE}$PERCENT%%${NC})         "
        fi
        
        if [ "$STATUS" == "completed" ]; then
            echo -e "\r${GREEN}✓ Analysis complete!${NC}                    "
            break
        fi
        
        if [ "$STATUS" == "failed" ]; then
            echo -e "\r${RED}✗ Analysis failed!${NC}                    "
            break
        fi
        
        sleep 10
    done
fi
