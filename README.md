# Volatility 3 Memory Forensics Automation Platform

## Architecture Overview

Enterprise-grade memory forensics platform built for Linux VPS deployment, featuring automated Volatility 3 analysis, artifact extraction, and web-based visualization.

## System Components

### Backend Stack
- **FastAPI**: REST API server
- **Celery**: Distributed task queue
- **Redis**: Message broker and cache
- **PostgreSQL**: Metadata and results storage
- **Docker**: Container isolation

### Forensic Tools
- Volatility 3 (memory analysis)
- binwalk (firmware/binary analysis)
- exiftool (metadata extraction)

### Frontend
- React/Vue (dashboard and visualization)
- WebSocket (real-time job updates)

## Directory Structure

```
forensicweb/
├── backend/
│   ├── api/                    # FastAPI routes
│   ├── core/                   # Core business logic
│   ├── workers/                # Celery tasks
│   ├── models/                 # Database models
│   ├── schemas/                # Pydantic schemas
│   ├── utils/                  # Utilities
│   └── config.py               # Configuration
├── frontend/                   # Web UI
├── docker/                     # Docker configs
├── storage/                    # Data storage
│   ├── uploads/                # Memory images
│   ├── artifacts/              # Extracted files
│   ├── results/                # JSON outputs
│   └── logs/                   # Analysis logs
├── tests/                      # Test suites
└── deploy/                     # Deployment scripts
```

## Security Model

1. **Upload Validation**: Size limits, magic byte verification
2. **Process Isolation**: Containerized workers
3. **Authentication**: JWT-based API access
4. **Rate Limiting**: Per-IP and per-user
5. **Artifact Quarantine**: Sandboxed extraction zones

## Deployment

```bash
# Production deployment
docker-compose up -d

# Development mode
./scripts/dev.sh
```

## API Endpoints

- `POST /api/v1/upload` - Upload memory image
- `POST /api/v1/upload/from-url` - **Queue download from URL** (async, no size limit)
- `GET /api/v1/upload/status/{image_id}` - Check download/upload status
- `POST /api/v1/jobs` - Create analysis job
- `GET /api/v1/jobs/{job_id}` - Job status
- `GET /api/v1/results/{job_id}` - Analysis results
- `GET /api/v1/artifacts/{job_id}` - List artifacts
- `GET /api/v1/download/{artifact_id}` - Download artifact

## Supported Volatility Plugins

- pslist, pstree (process enumeration)
- netscan (network connections)
- cmdline (command line arguments)
- malfind (code injection detection)
- filescan, dumpfiles (file recovery)
- handles (handle enumeration)
- vadinfo (VAD tree analysis)

## Future Extensions

- Elasticsearch integration for full-text search
- YARA scanning of extracted regions
- Timeline correlation engine
- Multi-node worker cluster
- Automated IOC extraction
- MITRE ATT&CK mapping
