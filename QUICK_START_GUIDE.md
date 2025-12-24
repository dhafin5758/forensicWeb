# URL Download Feature - Entry Points & Quick Reference

## 🚀 How to Access the Feature

### 1. Web Browser (Graphical)
```
URL: http://localhost:8000
Location: "Download from URL" section
Input: Paste download link
Button: "Queue Download"
Status: Displays in real-time
```

### 2. Command Line (curl)
```bash
curl -X POST http://localhost:8000/api/v1/upload/from-url \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/memory.raw",
    "description": "My incident"
  }'
```

### 3. Bash Script (Automated)
```bash
bash examples/download_from_url.sh
```
Pre-configured workflow: queue → monitor → analyze

### 4. Python (Programmatic)
```python
python3 examples/download_from_url.py
```
Reusable `ForensicsClient` class + examples

---

## 📖 Documentation Entry Points

### By Use Case

**"I want to use it NOW"**
→ [URL_DOWNLOAD_QUICK_START.md](URL_DOWNLOAD_QUICK_START.md)

**"I need the API reference"**
→ [docs/API_GUIDE.md](docs/API_GUIDE.md)

**"Show me a bash example"**
→ [examples/download_from_url.sh](examples/download_from_url.sh)

**"Show me a Python example"**
→ [examples/download_from_url.py](examples/download_from_url.py)

**"What was implemented?"**
→ [CHANGELOG_URL_DOWNLOAD.md](CHANGELOG_URL_DOWNLOAD.md)

**"How does it work?"**
→ [docs/FEATURE_INTEGRATION.md](docs/FEATURE_INTEGRATION.md)

**"Complete guide"**
→ [docs/URL_DOWNLOAD.md](docs/URL_DOWNLOAD.md)

**"Navigation help"**
→ [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)

---

## 🔧 Configuration Entry Points

### Environment Variables (.env)
```bash
# Uses existing settings (no changes needed):
MAX_UPLOAD_SIZE_GB=10           # File size limit
UPLOAD_DIR=/var/forensics/uploads  # Storage location

# Optional override:
CELERY_SOFT_TIME_LIMIT=6900     # Download timeout (2h default)
```

### API Endpoints
```
POST /api/v1/upload/from-url       ← Queue download
GET  /api/v1/upload/status/{id}    ← Check progress
```

### Docker Compose
```bash
# No changes needed, just restart:
docker-compose restart

# Or full deployment:
docker-compose up -d
```

---

## 📊 Status Checking Entry Points

### Check Download Progress
```bash
# API Status
curl http://localhost:8000/api/v1/upload/status/{image_id}

# Flower Dashboard
open http://localhost:5555

# Logs
docker-compose logs -f worker | grep download
```

### Check System Health
```bash
# Health endpoint
curl http://localhost:8000/api/v1/health

# Container status
docker-compose ps

# Storage usage
du -sh /var/forensics/uploads
```

---

## 🆘 Troubleshooting Entry Points

### If Something Goes Wrong

**"Download failed"**
→ [docs/URL_DOWNLOAD.md](docs/URL_DOWNLOAD.md) → Troubleshooting

**"Check logs"**
```bash
docker-compose logs worker | grep -i "download\|error"
```

**"Monitor queue"**
```
http://localhost:5555 (Flower dashboard)
```

**"Reset/cleanup"**
```bash
# Remove stuck download
rm /var/forensics/uploads/{image_id}_*

# Restart worker
docker-compose restart worker
```

---

## 📚 Code Entry Points

### Frontend (Web UI)
**File:** `frontend/index.html`
- Function: `downloadFromURL()`
- Element: `url-input`, `url-description`, `url-status`

### Backend API
**File:** `backend/api/routes/upload.py`
- Endpoint: `upload_from_url()` 
- Helper: `get_upload_status()`

### Celery Task
**File:** `backend/workers/tasks.py`
- Task: `download_memory_image_from_url()`
- Queue: "analysis" (priority: 10)

### Database Schema
**File:** `backend/models/database.py`
- Table: `memory_images` (unchanged)
- Optional fields: `source`, `source_url`, `description`

---

## 🎯 Quick Actions

### Queue Download
```bash
# Web UI
→ Go to http://localhost:8000 → Enter URL → Click button

# Bash
→ bash examples/download_from_url.sh

# Curl
→ curl -X POST http://localhost:8000/api/v1/upload/from-url ...
```

### Check Status
```bash
# Web UI
→ Status updates automatically

# Bash
→ curl http://localhost:8000/api/v1/upload/status/{id}

# Flower
→ http://localhost:5555 (see all tasks)
```

### Start Analysis
```bash
# Once download completes, use image_id:
curl -X POST http://localhost:8000/api/v1/jobs \
  -d '{"memory_image_id": "<id>", "plugins": [...]}'
```

---

## 📈 Integration Checkpoints

### After Download Queued
- ✓ Receive image_id in response
- ✓ Can check status with GET /upload/status/{id}
- ✓ Celery task appears in Flower dashboard

### During Download
- ✓ Check progress: GET /upload/status/{id}
- ✓ Monitor logs: `docker-compose logs worker`
- ✓ View in Flower: http://localhost:5555

### After Download Complete
- ✓ Status shows "completed"
- ✓ Can use image_id for job creation
- ✓ File in /var/forensics/uploads/

### After Job Creation
- ✓ Works same as uploaded files
- ✓ Volatility plugins execute normally
- ✓ Results available in /results/
- ✓ Artifacts in /artifacts/

---

## 🎓 Learning Paths

### Fastest (5 minutes)
1. Web UI → Enter URL → Done
2. Check: http://localhost:8000

### Quick (15 minutes)
1. Read: [URL_DOWNLOAD_QUICK_START.md](URL_DOWNLOAD_QUICK_START.md)
2. Try: Web UI or bash script
3. Done

### Thorough (45 minutes)
1. Read: [DELIVERY_SUMMARY.md](DELIVERY_SUMMARY.md)
2. Read: [docs/URL_DOWNLOAD.md](docs/URL_DOWNLOAD.md)
3. Try: Examples
4. Done

### Complete (90 minutes)
1. Read all documentation
2. Review code changes
3. Run all examples
4. Test integration
5. Done

---

## 🎪 Demo Workflow

```bash
# 1. Queue download
curl -X POST http://localhost:8000/api/v1/upload/from-url \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"url":"https://example.com/memory.raw"}'

# Response:
{
  "image_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Download queued..."
}

# 2. Check status (repeat until completed)
curl http://localhost:8000/api/v1/upload/status/550e8400...

# 3. Create analysis job
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "memory_image_id": "550e8400...",
    "plugins": ["pslist","pstree","netscan"],
    "priority": 8
  }'

# Response:
{
  "id": "job_id_here",
  "status": "pending"
}

# 4. Get results (after analysis completes)
curl http://localhost:8000/api/v1/results/job_id_here
```

---

## 📋 File Reference

### Documentation
| File | Purpose | Read Time |
|------|---------|-----------|
| DELIVERY_SUMMARY.md | Overview | 5 min |
| URL_DOWNLOAD_QUICK_START.md | How-to | 10 min |
| docs/URL_DOWNLOAD.md | Complete | 30 min |
| DOCUMENTATION_INDEX.md | Navigation | 5 min |

### Code Examples
| File | Language | Purpose |
|------|----------|---------|
| examples/download_from_url.sh | Bash | Complete workflow |
| examples/download_from_url.py | Python | Reusable client |

### Implementation
| File | Change | Impact |
|------|--------|--------|
| backend/api/routes/upload.py | +75 lines | New endpoint |
| backend/schemas/api_schemas.py | +20 lines | New schema |
| backend/workers/tasks.py | +150 lines | New task |
| frontend/index.html | +95 lines | New UI |

---

## ✅ Verification Checklist

Before using, verify:
- ✓ Platform is running: `docker-compose ps`
- ✓ API is healthy: `curl http://localhost:8000/api/v1/health`
- ✓ Worker is running: `docker-compose logs worker | head`
- ✓ Redis is responding: `redis-cli ping`
- ✓ Database is connected: Check API logs

---

## 🔗 Quick Links

**Main Documentation**
- [FINAL_DELIVERY.md](FINAL_DELIVERY.md) - Complete summary
- [DELIVERY_SUMMARY.md](DELIVERY_SUMMARY.md) - What you got

**User Guides**
- [URL_DOWNLOAD_QUICK_START.md](URL_DOWNLOAD_QUICK_START.md) - Start here
- [docs/URL_DOWNLOAD.md](docs/URL_DOWNLOAD.md) - Full guide

**Examples**
- [examples/download_from_url.sh](examples/download_from_url.sh) - Bash
- [examples/download_from_url.py](examples/download_from_url.py) - Python

**Reference**
- [docs/API_GUIDE.md](docs/API_GUIDE.md) - API docs
- [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) - Navigation
- [CHANGELOG_URL_DOWNLOAD.md](CHANGELOG_URL_DOWNLOAD.md) - What changed

**Technical**
- [docs/FEATURE_INTEGRATION.md](docs/FEATURE_INTEGRATION.md) - Architecture
- [FEATURE_URL_DOWNLOAD.md](FEATURE_URL_DOWNLOAD.md) - Implementation

---

**Ready to get started? Pick a method above and go!** 🚀
