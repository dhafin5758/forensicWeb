# URL Download - Quick Start Guide

## For the Impatient

### Web UI (Easiest)
1. Go to http://localhost:8000
2. Scroll to "Download from URL" section
3. Paste your download link: `https://example.com/dumps/memory.raw`
4. Click "Queue Download"
5. Done! Server downloads in background ✅

### Command Line (Linux/Mac)
```bash
# Set your token
TOKEN="your_jwt_token_here"

# Queue download
curl -X POST http://localhost:8000/api/v1/upload/from-url \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/dumps/memory.raw",
    "description": "My test download"
  }'

# You'll get back:
# {
#   "image_id": "550e8400-e29b-41d4-a716-446655440000",
#   "message": "Download queued..."
# }

# Now check status anytime:
curl http://localhost:8000/api/v1/upload/status/550e8400-e29b-41d4-a716-446655440000
```

### Bash Script (Complete Workflow)
```bash
bash examples/download_from_url.sh
# Queues download → monitors progress → starts analysis
```

### Python Script (Automation)
```bash
python3 examples/download_from_url.py
# 3 example functions to copy/modify
```

## How It Works

```
You paste URL
    ↓
Server queues download (returns immediately)
    ↓
Server downloads in background (non-blocking)
    ↓
You can check status anytime
    ↓
When ready, create analysis job with same image_id
    ↓
Results work exactly like uploaded files
```

## Key Points

✅ **Returns immediately** (202 Accepted)  
✅ **Non-blocking** (server downloads in background)  
✅ **No browser limits** (server-side download)  
✅ **Perfect for large files** (10GB+)  
✅ **Progress tracking** (check status anytime)  
✅ **Works with everything** (same image_id as uploads)

## Common Scenarios

### Scenario 1: Large File from Dropbox
```bash
# Share link → Get download URL → Paste to web UI
# Done! Server handles the rest.
```

### Scenario 2: Automated Backup Analysis
```bash
for backup in backup1.raw backup2.raw backup3.raw; do
  curl -X POST http://localhost:8000/api/v1/upload/from-url \
    -H "Authorization: Bearer $TOKEN" \
    -d "{\"url\": \"https://backups.example.com/$backup\"}"
done
# All 3 downloads happen in parallel
```

### Scenario 3: Remote Storage (S3)
```bash
# Generate presigned URL
PRESIGNED=$(aws s3 presign s3://bucket/memory.raw)

# Paste to web UI
# Server handles secure download
```

## Status Codes Explained

| Code | Meaning |
|------|---------|
| 202 | Download queued! Check status later |
| 404 | Image not found (try again) |
| 400 | Invalid URL format (fix it and retry) |
| 504 | URL unreachable (check URL, server, network) |

## Check Status

```bash
# Is download still running?
curl http://localhost:8000/api/v1/upload/status/<image_id>

# Possible responses:
# "status": "downloading"  (20%)
# "status": "completed"    (ready to analyze!)
# "status": "error"        (something went wrong)
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "URL unreachable" | Verify URL works in browser |
| "Download stuck" | Check logs: `docker-compose logs worker` |
| "Timeout error" | File too large? Increase limit in `.env` |
| "Wrong image_id" | Copy from response carefully |

## Next Steps

Once download completes:

```bash
# Create analysis job (same as uploaded files)
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "memory_image_id": "<your_image_id>",
    "plugins": ["pslist", "pstree", "netscan"],
    "priority": 8
  }'
```

## Tips & Tricks

**Tip 1:** Use `&` to queue multiple downloads in parallel
```bash
bash examples/download_from_url.sh &
bash examples/download_from_url.sh &
bash examples/download_from_url.sh &
# All download simultaneously
```

**Tip 2:** Add description for organization
```json
{
  "url": "...",
  "description": "Production server incident - 2025-12-24"
}
```

**Tip 3:** Monitor in Flower dashboard
```
open http://localhost:5555
# See all download tasks in real-time
```

**Tip 4:** Script the full workflow
```bash
# Copy examples/download_from_url.sh
# Edit with your URLs and token
# Run once, fully automated
```

## Examples Provided

| File | Use Case |
|------|----------|
| `examples/download_from_url.sh` | Complete bash workflow |
| `examples/download_from_url.py` | Python client library |
| Web UI (http://localhost:8000) | Browser-based (easiest) |

## Full Documentation

Want more details? See:
- [docs/URL_DOWNLOAD.md](docs/URL_DOWNLOAD.md) - Complete guide
- [docs/API_GUIDE.md](docs/API_GUIDE.md) - API reference
- [FEATURE_URL_DOWNLOAD.md](FEATURE_URL_DOWNLOAD.md) - Implementation details

## One-Liners

### Queue download
```bash
curl -X POST http://localhost:8000/api/v1/upload/from-url \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/memory.raw"}'
```

### Check status
```bash
curl http://localhost:8000/api/v1/upload/status/<image_id>
```

### Start analysis (when ready)
```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"memory_image_id":"<image_id>","plugins":["pslist","pstree"]}'
```

---

**That's it! You now know how to use URL downloads.** 🎉

For complex scenarios, see the full documentation.
