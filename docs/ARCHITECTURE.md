# System Architecture - Technical Specification

## High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                │
├─────────────────────────────────────────────────────────────────────┤
│  Web Browser          │  Python Client      │  CLI Tools            │
│  (JavaScript)         │  (requests lib)     │  (curl, scripts)      │
└─────────────┬─────────┴──────────┬──────────┴───────────────────────┘
              │                    │
              │ HTTPS              │ HTTPS/REST
              ▼                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      PRESENTATION LAYER                             │
├─────────────────────────────────────────────────────────────────────┤
│                         Nginx (Reverse Proxy)                       │
│  • TLS termination                                                  │
│  • Rate limiting (5 uploads/hr, 60 API/min)                        │
│  • Static file serving                                              │
│  • Request routing                                                  │
│  • Load balancing (future)                                          │
└─────────────┬───────────────────────────────────────────────────────┘
              │
              │ HTTP (internal)
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      APPLICATION LAYER                              │
├─────────────────────────────────────────────────────────────────────┤
│                      FastAPI Application                            │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │  API Routes                                                    │ │
│  │  ├─ /upload (file streaming, validation, hashing)            │ │
│  │  ├─ /jobs (CRUD operations, status tracking)                 │ │
│  │  ├─ /results (query, filtering, pagination)                  │ │
│  │  ├─ /artifacts (listing, download, metadata)                 │ │
│  │  ├─ /auth (login, token refresh, user management)            │ │
│  │  └─ /health (system status, diagnostics)                     │ │
│  └───────────────────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │  Middleware Stack                                              │ │
│  │  ├─ CORS (cross-origin control)                              │ │
│  │  ├─ GZip compression                                          │ │
│  │  ├─ Request timing                                            │ │
│  │  ├─ JWT validation                                            │ │
│  │  └─ Exception handling                                        │ │
│  └───────────────────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │  Business Logic                                                │ │
│  │  ├─ Upload validator (size, ext, magic bytes)                │ │
│  │  ├─ Job orchestrator (task submission, monitoring)           │ │
│  │  ├─ Result aggregator (query builder, serialization)         │ │
│  │  └─ Security (auth, rate limiting, sanitization)             │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────┬───────────────────────────────────────────────────────┘
              │
              │ Task Queue (Redis)
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      PROCESSING LAYER                               │
├─────────────────────────────────────────────────────────────────────┤
│                      Celery Worker Pool                             │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │  Task Orchestrator                                             │ │
│  │  analyze_memory_image(job_id)                                 │ │
│  │    1. Load job metadata from DB                               │ │
│  │    2. Profile detection → detect_profile.delay()              │ │
│  │    3. Plugin execution → group([plugins]).apply_async()       │ │
│  │    4. Artifact extraction → extract_artifacts.delay()         │ │
│  │    5. Post-processing → group([artifacts]).apply_async()      │ │
│  │    6. Update job status → COMPLETED                           │ │
│  └───────────────────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │  Volatility 3 Runner                                          │ │
│  │  • Subprocess execution (timeout=3600s)                       │ │
│  │  • JSON output parsing (JSONL format)                         │ │
│  │  • Error handling & retry logic                               │ │
│  │  • Concurrent execution (semaphore: 3)                        │ │
│  │  Plugins:                                                      │ │
│  │    pslist, pstree, netscan, cmdline, malfind, filescan,      │ │
│  │    dumpfiles, handles, vadinfo, dlllist, modscan              │ │
│  └───────────────────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │  Artifact Post-Processor                                       │ │
│  │  ┌─────────────────────┐  ┌─────────────────────┐            │ │
│  │  │  binwalk Analyzer   │  │  exiftool Extractor│            │ │
│  │  │  • Signature scan    │  │  • Metadata parse  │            │ │
│  │  │  • File carving      │  │  • File type detect│            │ │
│  │  │  • Firmware extract  │  │  • JSON normalize  │            │ │
│  │  └─────────────────────┘  └─────────────────────┘            │ │
│  └───────────────────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │  Task Queues (Priority-based)                                 │ │
│  │  • analysis (priority: 10) - Main orchestrator               │ │
│  │  • plugins (priority: 5)   - Volatility execution            │ │
│  │  • postprocess (priority: 3) - binwalk, exiftool            │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────┬───────────────────────────────────────────────────────┘
              │
              │ Async I/O
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      DATA LAYER                                     │
├─────────────────────────────────────────────────────────────────────┤
│  ┌────────────────────┐  ┌────────────────────┐  ┌──────────────┐ │
│  │   PostgreSQL       │  │      Redis         │  │  Filesystem  │ │
│  │   (Metadata DB)    │  │  (Queue & Cache)   │  │  (Artifacts) │ │
│  ├────────────────────┤  ├────────────────────┤  ├──────────────┤ │
│  │ Tables:            │  │ Structures:        │  │ Directories: │ │
│  │ • users            │  │ • Task queues      │  │ • uploads/   │ │
│  │ • memory_images    │  │ • Result backend   │  │ • artifacts/ │ │
│  │ • analysis_jobs    │  │ • Session cache    │  │ • results/   │ │
│  │ • plugin_results   │  │ • Rate limit data  │  │ • logs/      │ │
│  │ • artifacts        │  │ • Token blacklist  │  │              │ │
│  ├────────────────────┤  ├────────────────────┤  ├──────────────┤ │
│  │ Features:          │  │ Features:          │  │ Layout:      │ │
│  │ • Async queries    │  │ • Pub/Sub          │  │ job_id/      │ │
│  │ • Connection pool  │  │ • Persistence      │  │   ├─ raw.bin │ │
│  │ • JSON fields      │  │ • Atomic ops       │  │   ├─ *.json  │ │
│  │ • Full-text search │  │ • TTL expiration   │  │   └─ dumps/  │ │
│  │ • Indexing         │  │                    │  │              │ │
│  └────────────────────┘  └────────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow - Upload & Analysis Pipeline

```
┌──────────┐
│  Client  │
└────┬─────┘
     │
     │ 1. POST /upload (multipart/form-data)
     ▼
┌──────────────────┐
│  Nginx           │ 2. Rate limit check (5/hr)
│  Rate Limiter    │    Size limit check (20GB)
└────┬─────────────┘
     │
     │ 3. Forward to API
     ▼
┌──────────────────┐
│  FastAPI         │ 4. Extension validation
│  Upload Handler  │    Magic byte check
│                  │    Stream to disk + SHA256
└────┬─────────────┘
     │
     │ 5. Create MemoryImage record
     ▼
┌──────────────────┐
│  PostgreSQL      │ 6. INSERT into memory_images
│  Database        │    Return image_id
└────┬─────────────┘
     │
     │ 7. Return UploadResponse
     ▼
┌──────────┐
│  Client  │ 8. Receives image_id
└────┬─────┘
     │
     │ 9. POST /jobs (create analysis job)
     ▼
┌──────────────────┐
│  FastAPI         │ 10. Validate image_id exists
│  Job Handler     │     Create AnalysisJob record
└────┬─────────────┘
     │
     │ 11. INSERT analysis_jobs
     ▼
┌──────────────────┐
│  PostgreSQL      │ 12. Status: PENDING
└────┬─────────────┘
     │
     │ 13. Queue Celery task
     ▼
┌──────────────────┐
│  Redis           │ 14. Task queued: analyze_memory_image
│  Task Queue      │     Priority: user-specified
└────┬─────────────┘
     │
     │ 15. Worker picks task
     ▼
┌──────────────────┐
│  Celery Worker   │ 16. Update job: PROFILING
│  Orchestrator    │     Execute profile detection
└────┬─────────────┘
     │
     │ 17. Spawn parallel tasks
     ├─────────────────────┬─────────────────┬─────────────────┐
     ▼                     ▼                 ▼                 ▼
┌─────────┐          ┌─────────┐       ┌─────────┐      ┌─────────┐
│ pslist  │          │ pstree  │       │ netscan │      │ malfind │
│ task    │          │ task    │       │ task    │      │ task    │
└────┬────┘          └────┬────┘       └────┬────┘      └────┬────┘
     │                    │                  │                 │
     │ 18. Execute vol3   │                  │                 │
     │     with timeout   │                  │                 │
     ▼                    ▼                  ▼                 ▼
┌──────────────────────────────────────────────────────────────────┐
│  Subprocess: vol -f image.raw -r json <plugin>                   │
└────┬─────────────────────────────────────────────────────────────┘
     │
     │ 19. Parse JSONL output
     │     Save to results/<job_id>/<plugin>.json
     ▼
┌──────────────────┐
│  Filesystem      │ 20. Store JSON results
└────┬─────────────┘
     │
     │ 21. Create PluginResult records
     ▼
┌──────────────────┐
│  PostgreSQL      │ 22. INSERT plugin_results
└────┬─────────────┘
     │
     │ 23. Extract artifacts (malfind regions)
     ▼
┌──────────────────┐
│  Celery Worker   │ 24. Dump suspicious regions
│  Extractor       │     Save to artifacts/<job_id>/
└────┬─────────────┘
     │
     │ 25. Post-process artifacts
     ├─────────────────────┬─────────────────┐
     ▼                     ▼
┌─────────────┐       ┌─────────────┐
│  binwalk    │       │  exiftool   │
│  analysis   │       │  metadata   │
└────┬────────┘       └────┬────────┘
     │                     │
     │ 26. Store results   │
     └─────────┬───────────┘
               ▼
┌──────────────────┐
│  PostgreSQL      │ 27. UPDATE artifacts table
│  + Filesystem    │     (binwalk_results, exiftool_metadata)
└────┬─────────────┘
     │
     │ 28. Update job: COMPLETED
     ▼
┌──────────────────┐
│  PostgreSQL      │ 29. UPDATE analysis_jobs
│                  │     status = 'completed'
│                  │     completed_at = NOW()
└────┬─────────────┘
     │
     │ 30. Client polls: GET /jobs/{id}
     ▼
┌──────────┐
│  Client  │ 31. Status: COMPLETED
│          │     Get results: GET /results/{id}
└──────────┘
```

## Security Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SECURITY LAYERS                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Layer 1: NETWORK SECURITY                                         │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ • Firewall (UFW): 22, 80, 443 only                           │  │
│  │ • TLS 1.2/1.3 (Let's Encrypt)                                │  │
│  │ • Rate limiting (Nginx):                                     │  │
│  │   - 5 uploads/hr per IP                                      │  │
│  │   - 60 API requests/min per IP                               │  │
│  │ • DDoS protection (optional: Cloudflare)                     │  │
│  └──────────────────────────────────────────────────────────────┘  │
│         │                                                            │
│         ▼                                                            │
│  Layer 2: AUTHENTICATION                                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ • JWT tokens (HS256, 24hr expiry)                            │  │
│  │ • bcrypt password hashing (cost: 12)                         │  │
│  │ • Token blacklist (Redis)                                    │  │
│  │ • Secure cookie flags (HttpOnly, Secure, SameSite)           │  │
│  │ • Future: 2FA, OAuth2, LDAP                                  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│         │                                                            │
│         ▼                                                            │
│  Layer 3: AUTHORIZATION                                            │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ • RBAC (Role-Based Access Control)                           │  │
│  │   - Admin: Full access                                       │  │
│  │   - Analyst: Create jobs, view own results                   │  │
│  │   - Viewer: Read-only                                        │  │
│  │ • Resource ownership verification                            │  │
│  │ • Principle of least privilege                               │  │
│  └──────────────────────────────────────────────────────────────┘  │
│         │                                                            │
│         ▼                                                            │
│  Layer 4: INPUT VALIDATION                                         │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ • File extension whitelist (.raw, .mem, .dmp, etc)           │  │
│  │ • Size limits (max 20GB configurable)                        │  │
│  │ • Magic byte verification                                    │  │
│  │ • Filename sanitization (path traversal prevention)          │  │
│  │ • Pydantic schema validation                                 │  │
│  │ • SQL injection prevention (parameterized queries)           │  │
│  └──────────────────────────────────────────────────────────────┘  │
│         │                                                            │
│         ▼                                                            │
│  Layer 5: PROCESS ISOLATION                                        │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ • Docker containers (isolated namespaces)                    │  │
│  │ • Resource limits:                                           │  │
│  │   - CPU: 2 cores per worker                                  │  │
│  │   - Memory: 8GB per worker                                   │  │
│  │   - PIDs: 200 max                                            │  │
│  │ • No privileged containers                                   │  │
│  │ • Read-only filesystems where possible                       │  │
│  │ • Subprocess execution without shell=True                    │  │
│  └──────────────────────────────────────────────────────────────┘  │
│         │                                                            │
│         ▼                                                            │
│  Layer 6: DATA PROTECTION                                          │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ • Encryption at rest (optional: LUKS, database TDE)          │  │
│  │ • Encryption in transit (TLS everywhere)                     │  │
│  │ • Secure artifact storage (quarantine zone)                  │  │
│  │ • Automated log sanitization (no passwords/tokens)           │  │
│  │ • Secure delete (shred) for sensitive data                   │  │
│  └──────────────────────────────────────────────────────────────┘  │
│         │                                                            │
│         ▼                                                            │
│  Layer 7: MONITORING & AUDIT                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ • Comprehensive logging (all actions)                        │  │
│  │ • Audit trail (who, what, when)                              │  │
│  │ • Anomaly detection (future)                                 │  │
│  │ • Security alerts (failed logins, suspicious activity)       │  │
│  │ • Regular security scans                                     │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Deployment Topology

```
┌────────────────────────────────────────────────────────────────────┐
│                      PRODUCTION TOPOLOGY                           │
└────────────────────────────────────────────────────────────────────┘

SINGLE NODE (Current Implementation):

                        ┌──────────────┐
                        │   Internet   │
                        └──────┬───────┘
                               │
                        ┌──────▼───────┐
                        │  Firewall    │
                        │  UFW/iptables│
                        └──────┬───────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                 VPS Host                    │
        │  ┌───────────────────────────────────────┐ │
        │  │         Docker Network                │ │
        │  │  ┌─────────────────────────────────┐ │ │
        │  │  │         Nginx Container         │ │ │
        │  │  │  :80, :443 → API :8000         │ │ │
        │  │  └──────────────┬──────────────────┘ │ │
        │  │                 │                     │ │
        │  │  ┌──────────────▼──────────────────┐ │ │
        │  │  │       FastAPI Container         │ │ │
        │  │  │  4 workers (Uvicorn)            │ │ │
        │  │  └──────────────┬──────────────────┘ │ │
        │  │                 │                     │ │
        │  │  ┌──────────────┼──────────────────┐ │ │
        │  │  │              │                   │ │ │
        │  │  │  ┌───────────▼────────────┐     │ │ │
        │  │  │  │  Celery Worker x2      │     │ │ │
        │  │  │  │  (Volatility 3)        │     │ │ │
        │  │  │  └───────────┬────────────┘     │ │ │
        │  │  │              │                   │ │ │
        │  │  └──────────────┼───────────────────┘ │ │
        │  │                 │                      │ │
        │  │  ┌──────────────┼──────────────────┐  │ │
        │  │  │ PostgreSQL   │   Redis          │  │ │
        │  │  │ :5432        │   :6379          │  │ │
        │  │  └──────────────┴──────────────────┘  │ │
        │  └──────────────────────────────────────┘  │
        │                                             │
        │  Volumes:                                   │
        │  • postgres_data (persistent)               │
        │  • redis_data (persistent)                  │
        │  • /var/forensics (bind mount)              │
        └─────────────────────────────────────────────┘


MULTI-NODE (Future Scaling):

                  ┌──────────────┐
                  │ Load Balancer│
                  │ (HAProxy/LB) │
                  └──┬─────┬─────┘
         ┌───────────┘     └───────────┐
         │                             │
    ┌────▼────┐                   ┌────▼────┐
    │ API     │                   │ API     │
    │ Node 1  │                   │ Node 2  │
    └────┬────┘                   └────┬────┘
         │                             │
         └─────────────┬───────────────┘
                       │
         ┌─────────────┴───────────────┐
         │                             │
    ┌────▼────┐                   ┌────▼────┐
    │ Worker  │                   │ Worker  │
    │ Node 1  │                   │ Node 2  │
    └────┬────┘                   └────┬────┘
         │                             │
         └─────────────┬───────────────┘
                       │
         ┌─────────────┼───────────────┐
         │             │               │
    ┌────▼────┐   ┌────▼────┐    ┌────▼────┐
    │PostgreSQL│   │  Redis  │    │ Shared  │
    │ Cluster │   │ Sentinel│    │ Storage │
    │(Primary/│   │  Cluster│    │(NFS/S3) │
    │Replica) │   │         │    │         │
    └─────────┘   └─────────┘    └─────────┘
```

## Technology Stack Details

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Web Server** | Nginx | 1.24 | Reverse proxy, static files, TLS |
| **API Framework** | FastAPI | 0.104 | REST API, async request handling |
| **ASGI Server** | Uvicorn | 0.24 | ASGI application server |
| **Task Queue** | Celery | 5.3 | Distributed task execution |
| **Message Broker** | Redis | 7.0 | Task queue, cache, sessions |
| **Database** | PostgreSQL | 15 | Metadata, jobs, results |
| **ORM** | SQLAlchemy | 2.0 | Async database operations |
| **Validation** | Pydantic | 2.5 | Request/response schemas |
| **Auth** | PyJWT | 2.8 | Token generation/validation |
| **Password Hash** | bcrypt | via passlib | Secure password storage |
| **Container** | Docker | 24+ | Application isolation |
| **Orchestration** | Docker Compose | 2.0+ | Multi-container management |
| **Forensics** | Volatility 3 | Latest | Memory analysis framework |
| **Binary Analysis** | binwalk | Latest | Firmware extraction |
| **Metadata** | exiftool | Latest | File metadata extraction |
| **OS** | Ubuntu/Debian | 20.04+ | Linux VPS platform |

---

**This architecture is designed for:**
- ✅ Production deployment on single VPS
- ✅ Horizontal scaling (add more workers)
- ✅ High availability (future: multi-node)
- ✅ Security (defense in depth)
- ✅ Maintainability (clear separation of concerns)
- ✅ Observability (logging, monitoring, metrics)
