# Central Attendance Management System (CAMS)

A high-performance, enterprise-grade backend service built with Python 3.12, FastAPI, PyMongo Async, Pydantic v2, APScheduler, and Docker. CAMS provides deterministic attendance policy enforcement, multi-session tracking, leave workflows, and scheduled compliance monitoring.

> 📖 **Complete Documentation**: For the detailed file-by-file architecture guide, policy rules, and step-by-step Swagger testing workflows, see **[PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md)**.

---

## 1. Key Architectural Decisions

- **Direct PyMongo Async (`AsyncMongoClient`)**: Pure asynchronous MongoDB driver usage without Motor, SQLAlchemy, or relational ORMs.
- **Deterministic Policy Engine**: Compliance calculations are purely stateless, deterministic, and mathematical. No LLMs are used for compliance scoring.
- **Scheduler Isolation**: APScheduler runs as an isolated worker service (in a separate container/process), preventing execution contention and duplicate triggers across API replicas.
- **Interval Merging for Session De-duplication**: Overlapping sessions on the same day are merged using timeline interval math, ensuring exact office hour credit without double counting.
- **Timezone Architecture**: All timestamps are persisted as UTC-aware datetimes internally; displayed and converted to the company timezone (`Asia/Kolkata` by default).
- **Proportional Threshold Adjustments**: Holidays and approved leaves adjust the required weekly attendance days and hours proportionally using ceiling integer math for days and floating-point math for hours.
- **Security & RBAC**: Argon2 password hashing via `pwdlib`, HS256 JWT tokens with role-based access control (`admin`, `super_admin`, `manager`, `employee`), and CSV formula injection defenses (`=`, `+`, `-`, `@` escaping).

---

## 2. Technology Stack

| Component | Technology | Version |
| :--- | :--- | :--- |
| Runtime | Python | 3.12+ (tested on 3.11/3.12) |
| Framework | FastAPI | 0.115.5 |
| ASGI Server | Uvicorn | 0.32.1 |
| Database | MongoDB & PyMongo (Async) | PyMongo 4.10.1 / MongoDB 7.0 |
| Data Validation | Pydantic v2 & Pydantic Settings | 2.10.3 / 2.6.1 |
| Authentication | PyJWT & Argon2 (pwdlib) | PyJWT 2.10.1 / pwdlib 0.2.1 |
| Job Scheduler | APScheduler | 3.10.4 |
| Testing Suite | Pytest & Pytest-Asyncio | Pytest 8.3.4 / 0.24.0 |
| Linter & Formatter | Ruff | 0.8.4 |
| Containerization | Docker & Docker Compose | Docker Engine 24+ |

---

## 3. MongoDB Collections & Indexes

CAMS initializes indexes idempotently on startup across 7 core collections:

| Collection | Key Indexes |
| :--- | :--- |
| `employees` | Unique: `employee_id`, Unique: `email`, Compound/Single: `department`, `is_active`, `name` |
| `attendance` | Unique: `attendance_id`, Compound: `(employee_id, date)`, `(employee_id, date, entry_time)`, Single: `attendance_status`, `date` |
| `leave_requests` | Unique: `leave_id`, Compound: `(employee_id, start_date, end_date)`, Single: `status` |
| `holidays` | Unique: `holiday_id`, Unique: `date` |
| `notification_logs` | Unique: `notification_id`, Compound: `(employee_id, week_start, notification_type)` (deduplication) |
| `audit_logs` | Compound: `(timestamp, actor_id)`, `(resource_type, resource_id)` |
| `admin_users` | Unique: `admin_id`, Unique: `username`, Unique: `email` |

---

## 4. Policy Engine Rules

The compliance engine evaluates **completed policy weeks** (Monday 00:00 to Monday 00:00 exclusive in the company timezone).

1. **Minimum Qualifying Days**: Default 3 days/week. A qualifying day is a distinct date with at least one complete session.
2. **Minimum Hours per Week**: Default 15.0 valid office hours.
3. **Minimum Average Hours per Attended Day**: Default 5.0 hours/day across qualifying attended days.
4. **Session Calculation**:
   - Only sessions with both valid entry and exit (`exit > entry`) count toward hours.
   - Incomplete sessions (clocked-in without clock-out) count as `0.0` hours and are flagged as `incomplete`.
   - Overlapping sessions on the same day are de-duplicated via interval union merging.
5. **Leave & Holiday Proportional Adjustment**:
   - $\text{Eligible Days} = \text{Working Days} - (\text{Holidays} + \text{Approved Leaves})$.
   - $\text{Adjusted Min Days} = \min(\text{Eligible Days}, \lceil \text{Min Days} \times \frac{\text{Eligible Days}}{\text{Working Days}} \rceil)$.
   - $\text{Adjusted Min Hours} = \text{Min Hours} \times \frac{\text{Eligible Days}}{\text{Working Days}}$.

---

## 5. API Reference

All v1 routes are mounted under `/api/v1`. Interactive Swagger UI is available at `/docs` and ReDoc at `/redoc`.

### Health & Monitoring
- `GET /health/live`: Process liveness probe.
- `GET /health/ready`: Database connectivity readiness probe.

### Authentication (`/api/v1/auth`)
- `POST /api/v1/auth/login`: Admin and manager login. Returns JWT access token.
- `GET /api/v1/auth/me`: Retrieve current authenticated profile.

### Employee Management (`/api/v1/employees`)
- `POST /api/v1/employees`: Create new employee (admin role required).
- `GET /api/v1/employees`: List employees with pagination, search, and department filtering.
- `GET /api/v1/employees/{id}`: Retrieve employee by ID.
- `PUT /api/v1/employees/{id}`: Update employee details.
- `DELETE /api/v1/employees/{id}`: Soft delete (sets `is_active = False`).

### Attendance Sessions (`/api/v1/attendance`)
- `POST /api/v1/attendance/entry`: Clock-in (accepts simple "09:00" time string, checks collision).
- `POST /api/v1/attendance/exit`: Clock-out (calculates duration, immediately dispatches email if < 5 hrs).
- `POST /api/v1/attendance/quick-record`: Record entry + exit in a single call with automatic policy evaluation.
- `GET /api/v1/attendance/{id}/date/{date}`: Retrieve all sessions for a specific date.
- `GET /api/v1/attendance/{id}/history`: Paginated session history.
- `PATCH /api/v1/attendance/session/{id}`: Administrative manual correction with audit logging.

### Reporting & Compliance (`/api/v1/reports`)
- `GET /api/v1/reports/attendance`: Unified reporting endpoint.
  - Query parameters:
    - `period`: `daily` | `weekly` | `monthly` | `yearly` | `custom`
    - `date`: `YYYY-MM-DD` (for daily)
    - `start_date`, `end_date`: `YYYY-MM-DD` (for weekly/custom)
    - `year`, `month`: integers (for monthly/yearly)
    - `department`, `is_active`, `page`, `page_size`
- `GET /api/v1/reports/attendance/export.csv`: Download sanitized attendance report CSV.

### Leaves & Holidays (`/api/v1/leave` and `/api/v1/holidays`)
- `POST /api/v1/leave`: Submit employee leave request (self-service or admin).
- `GET /api/v1/leave`: List leave requests with status or employee_id filtering.
- `PATCH /api/v1/leave/{id}/approve`: Approve pending leave (excuses absent days in policy).
- `PATCH /api/v1/leave/{id}/reject`: Reject pending leave.
- `POST /api/v1/holidays`: Create company holiday.
- `GET /api/v1/holidays`: List company holidays.

### Administration (`/api/v1/admin`)
- `POST /api/v1/admin/users`: Provision admin/manager accounts.
- `GET /api/v1/admin/audit-logs`: Immutable audit trails.
- `POST /api/v1/admin/monitoring/run`: Manually trigger evaluation worker cycle (includes current week option).

---

## 6. Local Setup and Development

### Prerequisites
- Python 3.12+ (or 3.11+)
- MongoDB running locally at `localhost:27017` (or via Docker)

### Installation

```bash
# 1. Clone repository and navigate to directory
cd central-attendance-system

# 2. Create and activate virtual environment
python -m venv venv
# On Windows PowerShell:
.\venv\Scripts\Activate.ps1
# On Linux/macOS:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment configuration
cp .env.example .env
```

### Initial Data Setup

```bash
# Create initial admin user
python scripts/create_admin.py

# Seed database with sample employees, holidays, leaves, and attendance sessions
python scripts/seed_data.py
```

### Running Services

```bash
# Start FastAPI application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Start APScheduler worker in separate terminal
python -m app.workers.scheduler
```

---

## 7. Running with Docker Compose

To run the complete production-style setup (MongoDB, FastAPI API, and isolated Scheduler worker):

```bash
# Build and launch all services in background
docker compose up -d --build

# View container status
docker compose ps

# Tail logs
docker compose logs -f api
docker compose logs -f scheduler

# Stop services
docker compose down

# Stop and wipe database volume
docker compose down -v
```

---

## 8. Testing & Code Quality

Run tests using pytest:

```bash
# Run entire test suite
pytest -v

# Run specific unit tests
pytest tests/unit/ -v

# Run API endpoint tests
pytest tests/api/ -v
```

Check and format code with Ruff:

```bash
# Verify linting
ruff check app/ tests/ scripts/

# Format code
ruff format --check app/ tests/ scripts/
```
