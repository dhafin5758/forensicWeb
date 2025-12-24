# API Usage Guide

## Overview

Complete guide to using the Volatility 3 Memory Forensics Platform API.

## Authentication

All API endpoints (except `/health` and `/docs`) require authentication.

### Get Access Token

```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "analyst",
    "password": "secure_password"
  }'

# Response
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_at": "2024-12-25T10:30:00Z"
}
```

### Use Token in Requests

```bash
curl -H "Authorization: Bearer <your_token>" \
  http://localhost:8000/api/v1/jobs
```

## Complete Workflow

### Step 1: Upload Memory Image

```bash
# Upload a memory dump
curl -X POST http://localhost:8000/api/v1/upload/ \
  -H "Authorization: Bearer <token>" \
  -F "file=@/path/to/memory.raw"

# Response
{
  "image_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "550e8400_memory.raw",
  "file_size_bytes": 4294967296,
  "file_hash_sha256": "a3b5c7d9...",
  "uploaded_at": "2024-12-24T10:00:00Z",
  "message": "Upload successful"
}
```

### Alternative: Download from URL (Async)

For large files or remote sources, queue an asynchronous download:

```bash
# Queue download from URL (returns immediately)
curl -X POST http://localhost:8000/api/v1/upload/from-url \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/dumps/memory.raw",
    "description": "Linux server memory - 2025-12-24"
  }'

# Response (202 Accepted - download happens in background)
{
  "image_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "550e8400_downloading",
  "file_size_bytes": 0,
  "file_hash_sha256": "pending",
  "uploaded_at": "2024-12-24T10:00:00Z",
  "message": "Download queued - task is running in background. Check status with GET /upload/status/{image_id}"
}
```

**Check download status:**

```bash
# Monitor download progress
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/upload/status/550e8400-e29b-41d4-a716-446655440000

# Response (while downloading)
{
  "image_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "downloading",
  "downloaded_bytes": 2147483648,
  "total_bytes": 4294967296,
  "percent_complete": 50
}

# Response (after completion)
{
  "image_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "filename": "550e8400_downloaded",
  "file_size_bytes": 4294967296,
  "file_hash_sha256": "a3b5c7d9...",
  "downloaded_at": "2024-12-24T10:15:00Z"
}
```

**Benefits of URL downloads:**
- ✅ No browser upload size limits
- ✅ Server downloads in background (non-blocking)
- ✅ Ideal for remote storage (S3, GCS, etc)
- ✅ Memory efficient (streaming)
- ✅ Progress tracking available
- ✅ Automatic retry on failure
- ✅ Perfect for large files (10GB+)

### Step 2: Create Analysis Job

```bash
# Start analysis
curl -X POST http://localhost:8000/api/v1/jobs/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "memory_image_id": "550e8400-e29b-41d4-a716-446655440000",
    "plugins": ["pslist", "pstree", "netscan", "cmdline", "malfind"],
    "priority": 8
  }'

# Response
{
  "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "status": "pending",
  "memory_image_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2024-12-24T10:05:00Z",
  "total_plugins": 5,
  "completed_plugins": 0
}
```

### Step 3: Monitor Job Progress

```bash
# Check job status
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/jobs/7c9e6679-7425-40de-944b-e07fc1f90ae7

# Response
{
  "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "status": "analyzing",
  "memory_image_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2024-12-24T10:05:00Z",
  "started_at": "2024-12-24T10:05:30Z",
  "completed_at": null,
  "total_plugins": 5,
  "completed_plugins": 3,
  "failed_plugins": 0,
  "artifacts_extracted": 12
}
```

### Step 4: Retrieve Results

```bash
# Get all results for a job
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/results/7c9e6679-7425-40de-944b-e07fc1f90ae7

# Response
{
  "job_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "status": "completed",
  "plugins": [
    {
      "id": "abc123...",
      "plugin_name": "pslist",
      "success": true,
      "row_count": 156,
      "execution_time_seconds": 12.5
    },
    {
      "plugin_name": "netscan",
      "success": true,
      "row_count": 42,
      "execution_time_seconds": 8.3
    }
  ],
  "artifacts_count": 15
}
```

### Step 5: Get Detailed Plugin Data

```bash
# Get pslist results
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/v1/results/7c9e6679.../plugin/pslist?limit=10"

# Response
{
  "plugin_name": "pslist",
  "success": true,
  "row_count": 156,
  "result_data": [
    {
      "PID": 4,
      "PPID": 0,
      "ImageFileName": "System",
      "Offset": "0xfa8000000000",
      "Threads": 120,
      "Handles": 4567
    },
    {
      "PID": 392,
      "PPID": 4,
      "ImageFileName": "smss.exe",
      "Offset": "0xfa8000001000",
      "Threads": 2,
      "Handles": 52
    }
  ]
}
```

### Step 6: List Artifacts

```bash
# Get extracted artifacts
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/artifacts/7c9e6679-7425-40de-944b-e07fc1f90ae7

# Response
{
  "job_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "artifacts": [
    {
      "id": "def456...",
      "artifact_type": "malfind_region",
      "source_plugin": "malfind",
      "filename": "pid_1234_region_0x7ffe0000.bin",
      "file_size_bytes": 4096,
      "file_hash_sha256": "b4c8d9e1...",
      "process_pid": 1234,
      "process_name": "suspicious.exe",
      "binwalk_analyzed": true,
      "exiftool_analyzed": true
    }
  ],
  "total": 15
}
```

### Step 7: Download Artifact

```bash
# Download an artifact
curl -H "Authorization: Bearer <token>" \
  -o artifact.bin \
  http://localhost:8000/api/v1/artifacts/download/def456...

# The file is saved as artifact.bin
```

## Advanced Usage

### Filter Results

```bash
# Get only failed plugins
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/v1/jobs?status_filter=failed"

# Search artifacts by hash
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/v1/artifacts/filter?file_hash=a3b5c7d9..."
```

### Download Raw Plugin Output

```bash
# Download original JSON file
curl -H "Authorization: Bearer <token>" \
  -o pslist.json \
  http://localhost:8000/api/v1/results/7c9e6679.../plugin/pslist/download
```

### Job Management

```bash
# Cancel a running job
curl -X DELETE -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/jobs/7c9e6679.../cancel

# Retry a failed job
curl -X POST -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/jobs/7c9e6679.../retry
```

## Python Client Example

```python
import requests
from pathlib import Path

class ForensicsClient:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url
        self.token = self._login(username, password)
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def _login(self, username: str, password: str) -> str:
        """Authenticate and get token."""
        response = requests.post(
            f"{self.base_url}/api/v1/auth/login",
            json={"username": username, "password": password}
        )
        response.raise_for_status()
        return response.json()["access_token"]
    
    def upload_image(self, file_path: Path) -> str:
        """Upload memory image and return image ID."""
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(
                f"{self.base_url}/api/v1/upload/",
                headers=self.headers,
                files=files
            )
        response.raise_for_status()
        return response.json()["image_id"]
    
    def create_job(self, image_id: str, plugins: list = None) -> str:
        """Create analysis job and return job ID."""
        payload = {
            "memory_image_id": image_id,
            "plugins": plugins,
            "priority": 5
        }
        response = requests.post(
            f"{self.base_url}/api/v1/jobs/",
            headers=self.headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()["id"]
    
    def get_job_status(self, job_id: str) -> dict:
        """Get job status and progress."""
        response = requests.get(
            f"{self.base_url}/api/v1/jobs/{job_id}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def get_results(self, job_id: str) -> dict:
        """Get all results for a job."""
        response = requests.get(
            f"{self.base_url}/api/v1/results/{job_id}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def get_plugin_data(self, job_id: str, plugin_name: str, limit: int = None) -> dict:
        """Get detailed data from a specific plugin."""
        url = f"{self.base_url}/api/v1/results/{job_id}/plugin/{plugin_name}"
        if limit:
            url += f"?limit={limit}"
        
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def download_artifact(self, artifact_id: str, output_path: Path):
        """Download an artifact to file."""
        response = requests.get(
            f"{self.base_url}/api/v1/artifacts/download/{artifact_id}",
            headers=self.headers,
            stream=True
        )
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

# Usage
if __name__ == "__main__":
    # Initialize client
    client = ForensicsClient(
        base_url="http://localhost:8000",
        username="analyst",
        password="password"
    )
    
    # Upload memory image
    image_id = client.upload_image(Path("/path/to/memory.raw"))
    print(f"Uploaded: {image_id}")
    
    # Create analysis job
    job_id = client.create_job(
        image_id=image_id,
        plugins=["pslist", "netscan", "malfind"]
    )
    print(f"Job created: {job_id}")
    
    # Monitor until complete
    import time
    while True:
        status = client.get_job_status(job_id)
        print(f"Status: {status['status']} - {status['completed_plugins']}/{status['total_plugins']}")
        
        if status['status'] in ['completed', 'failed']:
            break
        
        time.sleep(10)
    
    # Get results
    results = client.get_results(job_id)
    print(f"Extracted {results['artifacts_count']} artifacts")
    
    # Get process list
    pslist = client.get_plugin_data(job_id, "pslist", limit=100)
    for proc in pslist['result_data']:
        print(f"PID {proc['PID']}: {proc['ImageFileName']}")
```

## Bash Script Example

```bash
#!/bin/bash
# Complete analysis workflow

BASE_URL="http://localhost:8000"
TOKEN="your_access_token_here"

# Function to make authenticated requests
api_call() {
    curl -s -H "Authorization: Bearer $TOKEN" "$@"
}

# Upload memory image
echo "Uploading memory image..."
UPLOAD_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/upload/" \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@memory.raw")

IMAGE_ID=$(echo $UPLOAD_RESPONSE | jq -r '.image_id')
echo "Image ID: $IMAGE_ID"

# Create job
echo "Creating analysis job..."
JOB_RESPONSE=$(api_call -X POST "$BASE_URL/api/v1/jobs/" \
    -H "Content-Type: application/json" \
    -d "{
        \"memory_image_id\": \"$IMAGE_ID\",
        \"plugins\": [\"pslist\", \"netscan\", \"malfind\"],
        \"priority\": 7
    }")

JOB_ID=$(echo $JOB_RESPONSE | jq -r '.id')
echo "Job ID: $JOB_ID"

# Monitor job
echo "Monitoring job progress..."
while true; do
    STATUS_RESPONSE=$(api_call "$BASE_URL/api/v1/jobs/$JOB_ID")
    STATUS=$(echo $STATUS_RESPONSE | jq -r '.status')
    COMPLETED=$(echo $STATUS_RESPONSE | jq -r '.completed_plugins')
    TOTAL=$(echo $STATUS_RESPONSE | jq -r '.total_plugins')
    
    echo "[$STATUS] $COMPLETED/$TOTAL plugins completed"
    
    if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
        break
    fi
    
    sleep 10
done

# Download results
echo "Downloading results..."
api_call "$BASE_URL/api/v1/results/$JOB_ID" | jq '.' > results.json

echo "Analysis complete! Results saved to results.json"
```

## Health Check

```bash
# Check system health
curl http://localhost:8000/api/v1/health | jq '.'

# Response
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-12-24T10:00:00Z",
  "services": {
    "filesystem": "healthy",
    "volatility3": "healthy",
    "binwalk": "healthy",
    "exiftool": "healthy",
    "database": "healthy",
    "redis": "healthy",
    "celery_workers": "healthy"
  },
  "uptime_seconds": 3600.5
}
```

## Error Handling

### Common HTTP Status Codes

- **200 OK**: Request successful
- **201 Created**: Resource created
- **400 Bad Request**: Invalid input
- **401 Unauthorized**: Missing/invalid token
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource doesn't exist
- **413 Payload Too Large**: Upload exceeds limit
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Server error
- **503 Service Unavailable**: Service down

### Error Response Format

```json
{
  "error": "Validation Error",
  "detail": "File too large. Maximum size: 10 GB",
  "timestamp": "2024-12-24T10:00:00Z"
}
```

## Best Practices

1. **Always check job status** before requesting results
2. **Use pagination** for large result sets
3. **Implement retry logic** for transient failures
4. **Store tokens securely** (environment variables, secrets manager)
5. **Validate uploads** before submission
6. **Monitor rate limits** to avoid throttling
7. **Download artifacts to sandboxed environment**
8. **Use HTTPS** in production
9. **Rotate tokens regularly**
10. **Log all API interactions** for audit trail

## Interactive API Documentation

Visit `/docs` for interactive Swagger UI:
- http://localhost:8000/docs

Visit `/redoc` for alternative documentation:
- http://localhost:8000/redoc
