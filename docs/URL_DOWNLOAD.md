# URL Download Feature

## Overview

The URL Download feature allows you to provide a direct download link to a memory dump file, and the server will download it asynchronously in the background. This is ideal for:

- **Large files** (10GB+) that are slow to upload via browser
- **Remote storage** (S3, GCS, HTTP endpoints)
- **Automated pipelines** where files are already on a server
- **Non-blocking operations** (server fetches while you work)

## Why Use URL Download?

| Feature | Direct Upload | URL Download |
|---------|---------------|--------------|
| Browser limits | 2GB typical | None (server-side) |
| Upload speed | Network dependent | Depends on source location |
| Blocking | Yes (waits for upload) | No (returns immediately) |
| Progress | Yes (upload %) | Yes (download status) |
| Best for | < 1GB files | > 1GB files |
| Remote sources | No | Yes (S3, etc) |
| Automation | Limited | Excellent |

## API Endpoint

### POST `/api/v1/upload/from-url`

Queue a background download of a memory image from a URL.

**Request:**
```json
{
  "url": "https://example.com/dumps/memory.raw",
  "description": "Production server memory - 2025-12-24"
}
```

**Parameters:**
- `url` (required): Direct download URL (must start with http:// or https://)
- `description` (optional): Human-readable description

**Response (202 Accepted):**
```json
{
  "image_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "550e8400_downloading",
  "file_size_bytes": 0,
  "file_hash_sha256": "pending",
  "uploaded_at": "2024-12-24T10:00:00Z",
  "message": "Download queued - task is running in background..."
}
```

## Status Checking

### GET `/api/v1/upload/status/{image_id}`

Check the status of a download.

**Possible statuses:**

```json
{
  "status": "downloading",
  "image_id": "550e8400-e29b-41d4-a716-446655440000",
  "downloaded_bytes": 2147483648,
  "total_bytes": 4294967296,
  "percent_complete": 50
}
```

```json
{
  "status": "completed",
  "image_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "550e8400_downloaded",
  "file_size_bytes": 4294967296,
  "file_hash_sha256": "a3b5c7d9...",
  "downloaded_at": "2024-12-24T10:15:00Z"
}
```

```json
{
  "status": "error",
  "image_id": "550e8400-e29b-41d4-a716-446655440000",
  "error": "URL unreachable: Connection timeout"
}
```

## Usage Examples

### Bash/curl

```bash
# Queue download
RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/upload/from-url \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://storage.example.com/memory.raw",
    "description": "Server backup"
  }')

IMAGE_ID=$(echo $RESPONSE | jq -r '.image_id')
echo "Image ID: $IMAGE_ID"

# Check status
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/upload/status/$IMAGE_ID

# Once complete, create analysis job
curl -X POST http://localhost:8000/api/v1/jobs/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"memory_image_id\": \"$IMAGE_ID\",
    \"plugins\": [\"pslist\", \"pstree\", \"netscan\"],
    \"priority\": 8
  }"
```

See [download_from_url.sh](download_from_url.sh) for a complete bash example.

### Python

```python
from forensics_client import ForensicsClient

client = ForensicsClient(
    base_url='http://localhost:8000',
    token='your_jwt_token'
)

# Queue download
result = client.download_from_url(
    url='https://example.com/dumps/memory.raw',
    description='Production incident - 2025-12-24'
)
image_id = result['image_id']

# Check status
status = client.check_download_status(image_id)
print(f"Status: {status['status']}")

# When complete, start analysis
job = client.create_job(
    image_id=image_id,
    plugins=['pslist', 'pstree', 'netscan', 'cmdline', 'malfind'],
    priority=8
)
```

See [download_from_url.py](download_from_url.py) for complete Python examples.

### Web UI

1. Navigate to `http://localhost:8000`
2. Click the "Download from URL" tab
3. Paste your download URL
4. (Optional) Add a description
5. Click "Queue Download"
6. Click "Check Status" to monitor progress

## Security Considerations

### URL Validation
- URLs must start with `http://` or `https://`
- Maximum URL length: 2048 characters
- DNS resolution happens on server (potential SSRF risk in untrusted environments)

### Download Security
- Downloads are subject to the same size limits as file uploads
- SHA256 hash is calculated and stored for integrity verification
- Files are scanned before processing
- Downloaded files are stored in the same secure upload directory

### Recommendations
- Use HTTPS URLs only in production
- Implement network-level controls to restrict outbound connections
- Monitor for suspicious download patterns
- Enable audit logging for all downloads
- Consider implementing URL whitelisting for production environments

## Timeout and Limits

| Setting | Default | Configurable |
|---------|---------|--------------|
| Download timeout | 2 hours | `CELERY_SOFT_TIME_LIMIT` |
| Hard timeout | 2h 5min | `CELERY_TIME_LIMIT` |
| Max file size | 10GB | `MAX_UPLOAD_SIZE_GB` |
| Chunk size | 1MB | Internal |
| Retry attempts | 3 (automatic) | `CELERY_TASK_AUTORETRY_FOR` |

## Monitoring

### Check Download Queue
```bash
# View pending downloads
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/jobs?filter=downloading

# Monitor Flower dashboard
open http://localhost:5555
```

### Logs
```bash
# Watch worker logs
docker-compose logs -f worker | grep "download"

# Check API logs
docker-compose logs -f api | grep "URL download"
```

## Troubleshooting

### "URL unreachable"
- Verify the URL is publicly accessible
- Check network connectivity from VPS to remote host
- Ensure the URL returns HTTP 200 status
- Check for authentication requirements (basic auth, tokens, etc)

### "Download timeout"
- File is too large for 2-hour timeout
- Network connection is unstable
- Remote server is slow
- Solution: Increase `CELERY_SOFT_TIME_LIMIT` in .env

### "File validation failed"
- File is smaller than 1KB
- File exceeds size limits (default: 10GB)
- File format not supported
- Solution: Check file integrity at source

### Download stuck in "downloading" state
- Network connection lost
- Remote server dropped connection
- Check logs: `docker-compose logs worker`
- Manually cancel and retry (future feature)

## Examples Provided

### 1. **download_from_url.sh** (Bash)
Complete workflow: download → status check → analysis job
```bash
bash examples/download_from_url.sh
```

### 2. **download_from_url.py** (Python)
Three examples:
- Single large file download
- Download and immediate analysis
- Batch parallel downloads

```bash
python3 examples/download_from_url.py
```

## Advanced Usage

### S3 Bucket Download
```bash
# Generate pre-signed URL
AWS_REGION=us-east-1
BUCKET=forensics-dumps
KEY=2025-12-24/server01-memory.raw

PRESIGNED_URL=$(aws s3 presign \
  s3://$BUCKET/$KEY \
  --region $AWS_REGION \
  --expires-in 3600)

# Queue download
curl -X POST http://localhost:8000/api/v1/upload/from-url \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"$PRESIGNED_URL\"}"
```

### Google Cloud Storage Download
```bash
# Generate signed URL (service account JSON)
BUCKET=forensics-dumps
OBJECT=2025-12-24/server01-memory.raw

gsutil signurl -d 1h \
  ~/gcs-key.json \
  gs://$BUCKET/$OBJECT

# Then use the signed URL with our API
```

### Automated Incident Response Pipeline
```bash
#!/bin/bash
# Download all backups from a date and analyze them

BACKUP_DATE="2025-12-24"
SERVERS=("web01" "web02" "db01" "cache01")

for SERVER in "${SERVERS[@]}"; do
    URL="https://backups.company.com/$BACKUP_DATE/$SERVER-memory.raw"
    
    # Queue download
    RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/upload/from-url \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "{\"url\": \"$URL\", \"description\": \"$SERVER - $BACKUP_DATE\"}")
    
    IMAGE_ID=$(echo $RESPONSE | jq -r '.image_id')
    echo "Queued $SERVER: $IMAGE_ID"
done
```

## Performance Tips

1. **Use server-side downloads for large files**
   - Avoids browser timeouts
   - Better network efficiency
   - Can leverage direct server-to-server transfers

2. **Batch multiple downloads**
   - Queue 5-10 downloads in parallel
   - Workers process independently
   - Better utilization of resources

3. **Monitor queue depth**
   - If queue > 10, consider scaling workers
   - Check Flower dashboard (http://localhost:5555)

4. **Use description field**
   - Include dates, server names, incident IDs
   - Helps with later searching and auditing
   - Searchable in API responses

## Comparison: When to Use What

### Use Direct Upload (`/upload`) when:
- ✅ File < 1GB
- ✅ Browser upload is acceptable
- ✅ File is on your local machine
- ✅ Fast network connection
- ✅ Low latency required

### Use URL Download (`/upload/from-url`) when:
- ✅ File > 1GB
- ✅ File is on remote server/storage
- ✅ Don't want to wait for upload
- ✅ Automated pipeline
- ✅ Server-to-server transfer
- ✅ Multiple files to process

## Limitations & Future Enhancements

### Current Limitations
- ❌ No authentication/credentials support (public URLs only)
- ❌ No download pause/resume
- ❌ No per-URL bandwidth limiting
- ❌ No concurrent downloads limit (per task)

### Planned Features
- ✅ HTTP Basic Auth support
- ✅ Download pause/resume (partial downloads)
- ✅ Concurrent download limits
- ✅ Bandwidth limiting per download
- ✅ Retry with exponential backoff
- ✅ FTP/SFTP support
- ✅ Download result webhooks
- ✅ S3/GCS native integration

## Related Documentation

- [API Guide](../docs/API_GUIDE.md) - Full API documentation
- [Deployment Guide](../docs/DEPLOYMENT.md) - Setup and configuration
- [Quick Reference](../docs/QUICK_REFERENCE.md) - Common commands
- [ARCHITECTURE.md](../docs/ARCHITECTURE.md) - System design

## Support

For issues or questions:
1. Check logs: `docker-compose logs worker`
2. Test connectivity to URL manually
3. Review [Troubleshooting](#troubleshooting) section
4. Check API status: `curl http://localhost:8000/api/v1/health`
