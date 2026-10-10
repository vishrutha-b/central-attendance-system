# Central Attendance Management System - Repository Conventions

## Architecture Decisions

### Technology Stack
- Python 3.12, FastAPI, MongoDB, PyMongo Async (AsyncMongoClient)
- Pydantic v2 + pydantic-settings for config/validation
- PyJWT + pwdlib[argon2] for auth and password hashing
- APScheduler for scheduled jobs (isolated from API workers)
- pytest + pytest-asyncio + httpx for tests
- ruff for linting/formatting

### Project Layout
- `app/` — application source code
- `app/api/v1/` — FastAPI route handlers
- `app/services/` — business logic (policy, reporting, etc.)
- `app/repositories/` — direct MongoDB CRUD wrappers
- `app/schemas/` — Pydantic request/response schemas
- `app/models/` — internal document models
- `app/database/` — connection lifecycle and index initialization
- `app/security/` — JWT and password utilities
- `app/email/` — SMTP client
- `app/workers/` — APScheduler setup and monitoring jobs
- `scripts/` — CLI utilities (seed data, admin creation)
- `tests/` — pytest tests (unit, integration, api)
- `docs/` — documentation

### Key Design Decisions
1. **AsyncMongoClient only** — no Motor, no SQLAlchemy, no PostgreSQL
2. **Policy Engine** is stateless and pure — `policy_service.py` calculates compliance from records
3. **Scheduler isolation** — APScheduler runs in a separate Docker service, never in Uvicorn workers
4. **UTC internally** — all timestamps stored as UTC-aware datetimes; converted to Asia/Kolkata for display
5. **Soft deletes** — employees are deactivated, never hard-deleted
6. **Single reporting endpoint** — `/api/v1/reports/attendance` handles all period types via query params
7. **Idempotent seed** — seed script uses upserts; safe to run multiple times
8. **No LLM for compliance** — compliance is calculated deterministically by policy_service.py

### MongoDB Collections
- `employees` — employee master data
- `attendance` — attendance sessions (entry/exit pairs)
- `leave_requests` — employee leave applications
- `holidays` — company holidays
- `notification_logs` — email delivery state and deduplication
- `audit_logs` — immutable audit history
- `admin_users` — administrator accounts

### Week Boundaries
- Default: Monday 00:00 to next Monday 00:00 (exclusive) in Asia/Kolkata
- Configurable via WEEK_START_DAY env var (0=Monday)
- Only completed weeks are evaluated for violations

### Compliance Rules (Defaults)
- MIN_DAYS_PER_WEEK=3
- MIN_HOURS_PER_WEEK=15
- MIN_AVG_HOURS_PER_DAY=5
- All thresholds configurable via environment

### Session Counting
- Only sessions with both entry AND exit count toward hours
- Overlapping sessions: hours de-duplicated using interval merging
- Incomplete session (no exit) = 0 hours, flagged as "incomplete"

## Commands

### Local Development
```powershell
# Windows PowerShell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Create admin
python scripts/create_admin.py

# Seed data
python scripts/seed_data.py

# Run API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run scheduler
python -m app.workers.scheduler

# Run tests
pytest tests/ -v

# Lint
ruff check app/ tests/
ruff format app/ tests/
```

```bash
# Linux/WSL
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Docker
```bash
docker compose build
docker compose up -d
docker compose logs -f api
docker compose logs -f scheduler
docker compose ps
docker compose down
docker compose down -v  # also removes volumes (data reset)
```

### MongoDB Compass
- Local: mongodb://localhost:27017
- Docker (Compass on host): mongodb://localhost:27017

## Secrets Management
- Copy `.env.example` to `.env` and fill in real values
- Never commit `.env` to version control
- JWT_SECRET must be at least 32 chars in production
- SMTP credentials must come from environment, never hardcoded

## Test Database
- Tests use database name `cams_test` (configured in conftest.py)
- Never run tests against production database
- mongomock used for unit tests; real MongoDB for integration tests
