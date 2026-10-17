# Central Attendance Management System (CAMS) — Complete Project Documentation

> **Version**: 1.0.0  
> **Tech Stack**: Python 3.12+, FastAPI, PyMongo Async (`AsyncMongoClient`), Pydantic v2, APScheduler, SMTP  
> **Database**: MongoDB 7.0 (`cams_dev`)  
> **Interactive API Docs (Swagger UI)**: `http://localhost:8000/docs`

---

## 1. Project Overview & Objectives

**Central Attendance Management System (CAMS)** is an enterprise-grade backend service built to automate office attendance tracking, enforce company work-from-home/office presence policies, handle leave workflows, and trigger instant policy alert notifications.

### Primary Business Objectives:
1. **Accurate Time Tracking**: Clock-in (Entry) and Clock-out (Exit) tracking with support for multiple sessions per day.
2. **Deterministic Policy Enforcement**: Strict, transparent rules that evaluate daily and weekly attendance compliance.
3. **Automated Real-Time Alerts**: The exact minute an employee clocks out before meeting the daily requirement (< 5 hours), the system sends an official alert email to that specific employee.
4. **Weekly Policy Auditing**: Automated monitoring cycles that evaluate weekly compliance (3 days/week, 15 hrs/week, 5 hrs/day average) and send warning emails for violations.
5. **Smart Leave Adjustments**: Approved leaves and company holidays automatically lower attendance thresholds so excused employees never receive wrongful non-compliance notices.

---

## 2. Company Attendance Policy (Core Rules)

| Requirement | Policy Rule | Threshold | Trigger / Action |
| :--- | :--- | :--- | :--- |
| **Mandatory Daily Hours** | Daily Office Presence | **≥ 5.0 hours/day** | **Instant Alert**: If an employee exits before 5.0 hours, an automated email is sent to them immediately upon exit. |
| **Mandatory Weekly Days** | Qualifying In-Office Days | **≥ 3 days/week** | **Weekly Monitoring**: Evaluated at week close; flags employee if < 3 days attended. |
| **Mandatory Weekly Hours** | Total Weekly Office Hours | **≥ 15.0 hours/week** | **Weekly Monitoring**: Evaluated at week close; flags employee if < 15.0 hours logged. |
| **Daily Average** | Average Hours per Attended Day | **≥ 5.0 hours/day** | **Weekly Monitoring**: Total hours divided by attended days must be ≥ 5.0. |
| **Excused Absence (Leave)** | Approved Leave Days | Excused | Automatically reduces required weekly days & hours proportionally. |
| **Company Holidays** | Official Holidays | Excused | Automatically reduces required weekly days & hours proportionally. |

---

## 3. Project Directory & File-by-File Guide

Below is the complete architectural map of every file and directory in the repository:

```
central-attendance-system/
├── .env                              # Environment variables (DB, JWT, SMTP, thresholds)
├── pyproject.toml                    # Project dependencies, build configuration, ruff & pytest configs
├── requirements.txt                  # Python package requirements
├── README.md                         # Quickstart overview
├── PROJECT_DOCUMENTATION.md          # Complete comprehensive technical and user guide (This document)
│
├── app/                              # Main application package
│   ├── config.py                     # Pydantic BaseSettings: loads and validates all .env variables
│   ├── exceptions.py                 # Custom domain exception classes (404, 400, 409, 401, 403)
│   ├── logging_config.py             # Structured JSON & console logger configuration
│   ├── main.py                       # FastAPI application entrypoint, lifespan startup/shutdown
│   │
│   ├── api/                          # HTTP Presentation Layer
│   │   ├── dependencies.py           # FastAPI dependency injection (repos, services, auth, RBAC)
│   │   └── v1/                       # Version 1 API routers
│   │       ├── router.py             # Master router aggregating all V1 endpoints
│   │       ├── admin.py              # Admin users, audit logs, on-demand monitoring triggers
│   │       ├── attendance.py         # Entry, Exit, Quick-Record, and session history endpoints
│   │       ├── auth.py               # Administrator login (/login) and profile (/me) endpoints
│   │       ├── employees.py          # Employee CRUD (create, list, search, update, soft-delete)
│   │       ├── health.py             # Liveness (/health/live) and DB Readiness (/health/ready) probes
│   │       ├── leave.py              # Leave request submission, approval, rejection, and holidays
│   │       └── reports.py            # Attendance reports (daily, weekly, monthly, CSV export)
│   │
│   ├── database/                     # MongoDB Database Layer
│   │   ├── connection.py             # AsyncMongoClient lifecycle management (connect, disconnect)
│   │   └── indexes.py                # Idempotent index creation across all 7 collections
│   │
│   ├── repositories/                 # Data Access Layer (Direct PyMongo Async)
│   │   ├── admin_repo.py             # Admin users, audit logs, and notification logs queries
│   │   ├── attendance_repo.py        # Attendance session CRUD, date-based queries, open session checks
│   │   ├── employee_repo.py          # Employee CRUD, search regex queries, active checks
│   │   └── leave_repo.py             # Leave requests, overlapping checks, holidays collection queries
│   │
│   ├── schemas/                      # Pydantic v2 Models (Request/Response Validation)
│   │   ├── admin.py                  # Audit log response schemas
│   │   ├── attendance.py             # Entry/Exit requests, flexible time parser, session responses
│   │   ├── auth.py                   # Login request, JWT token response schemas
│   │   ├── common.py                 # Base model with alias generators and UTC serialization
│   │   ├── employee.py               # Employee create, update, and response schemas
│   │   ├── leave.py                  # Leave request, decision, and holiday schemas
│   │   └── reports.py                # Daily, weekly, monthly report summary schemas
│   │
│   ├── security/                     # Security, Cryptography & Tokens
│   │   ├── auth.py                   # PyJWT access token generation and decoding
│   │   └── password.py               # Argon2 password hashing and verification (pwdlib)
│   │
│   ├── services/                     # Business Logic Layer
│   │   ├── attendance_service.py     # Entry/Exit handling, duration math, daily policy email triggers
│   │   ├── audit_service.py          # Immutable audit logging helper for security & compliance
│   │   ├── employee_service.py       # Employee management logic and validation
│   │   ├── leave_service.py          # Leave creation, date overlap checks, approvals, holidays
│   │   ├── notification_service.py   # Multi-part HTML/plaintext email dispatcher & SMTP sender
│   │   ├── policy_service.py         # Deterministic compliance calculator (3 days, 15 hrs, 5 hrs/day)
│   │   └── report_service.py         # Summary aggregator, date range math, CSV export builder
│   │
│   ├── templates/                    # Executive HTML Email Templates
│   │   ├── daily_violation.html      # Responsive corporate HTML email for < 5 hours alert
│   │   └── weekly_violation.html     # Responsive corporate HTML email for weekly policy violation
│   │
│   └── workers/                      # Background Processing & Scheduling
│       ├── monitoring.py             # Compliance evaluation worker, retry logic, deduplication
│       └── scheduler.py              # APScheduler background runner for daily midnight audit
│
└── tests/                            # Test Suite (39 Automated Async Tests)
    ├── conftest.py                   # Pytest fixtures (async test client, auth headers, mock DB)
    ├── api/                          # End-to-end API integration tests
    │   ├── test_admin.py             # Tests for admin routes & RBAC
    │   ├── test_attendance.py        # Tests for entry, exit, quick-record, and email triggers
    │   ├── test_auth.py              # Tests for admin login & token validation
    │   ├── test_employees.py         # Tests for employee CRUD
    │   ├── test_health.py            # Tests for health probes
    │   ├── test_leave.py             # Tests for leave request and approval workflows
    │   └── test_reports.py           # Tests for daily/weekly reports & CSV export
    └── unit/                         # Pure unit tests (no network/DB)
        ├── test_policy_engine.py     # Deterministic policy compliance engine test matrix
        └── test_security.py          # Password hashing and JWT encoding/decoding tests
```

---

## 4. Key Workflows Explained

### Workflow 1: Employee Daily Attendance & Instant Deficit Alert (< 5 Hours)

```
                     1. Employee Records Entry
                      POST /api/v1/attendance/entry
                      {"employee_id": "EMP-007", "entry_time": "09:00"}
                                   │
                                   ▼
                      MongoDB saves open session
                      (status: "incomplete", entry: 09:00)
                                   │
                                   │
                     2. Employee Records Exit
                      POST /api/v1/attendance/exit
                      {"employee_id": "EMP-007", "exit_time": "12:00"}
                                   │
                ┌──────────────────┴──────────────────┐
                ▼                                     ▼
        Session Saved                       Policy Evaluator Check
     • exit_time: 12:00                    • Duration: (12:00 - 09:00) = 3.0 hrs
     • total_hours: 3.0 hrs                • Threshold: 5.0 hrs minimum
     • status: "complete"                  • Result: DEFICIT of -2.0 hrs
                                                      │
                                                      ▼
                                       Instant Automated Email Sent
                                    • Sent directly to employee's email
                                    • Executive HTML layout with badge
                                    • Full breakdown: Name, ID, Times, Deficit
```

- **If Exit is ≥ 5.0 hours (e.g. 15:00)**: Session is saved as `complete`, total hours = 6.0 hrs, **no alert email is sent** (policy fulfilled).
- **If Exit is < 5.0 hours (e.g. 12:00)**: Session is saved as `complete`, total hours = 3.0 hrs, **alert email is dispatched the exact second they exit**.

---

### Workflow 2: Self-Service Leave Request & Manager Approval

```
   1. Employee (Self-Service)
      POST /api/v1/leave
      (No Admin Token Required)
      • employee_id: "EMP-007"
      • leave_type: "sick" | "annual" | "casual"
      • start_date: "2026-10-12"
      • end_date: "2026-10-14"
      • reason: "Medical checkup"
           │
           ▼
      MongoDB saves request (status: "pending", id: "LV-XXXX")
           │
           │
   2. Manager Reviews & Approves
      PATCH /api/v1/leave/{leave_id}/approve
      (Requires Admin/Manager Token)
      • Status changes to "approved"
           │
           ▼
   3. Automatic Policy Protection
      • The weekly compliance engine detects the approved leave dates.
      • The mandatory weekly requirements (3 days / 15 hrs) are proportionally reduced.
      • The employee will NOT receive a violation email for absent days while on approved leave.
```

---

### Workflow 3: Weekly Compliance Monitoring Cycle

1. **When It Runs**:
   - Automatically via **APScheduler** every Sunday/Monday at midnight.
   - Or **on-demand anytime via Swagger**: `POST /api/v1/admin/monitoring/run`.
2. **What It Evaluates**:
   - `Rule 1`: Did the employee attend at least 3 qualifying days?
   - `Rule 2`: Did the employee complete at least 15.0 total office hours?
   - `Rule 3`: Was the average attendance at least 5.0 hours per attended day?
3. **If Non-Compliant**:
   - Sends the formatted **Weekly Attendance Policy Notice** listing all detected violations.
   - Saves a record in `notification_logs` with a unique deduplication key (`EMP-007::2026-10-05::violation`) so duplicate emails are never sent.

---

## 5. Email System Setup (Console vs Real Gmail SMTP)

In [`.env`](file:///c:/Users/vishr/OneDrive/Documents/vishu%20backend/central-attendance-system/.env), configure the `EMAIL_DELIVERY_MODE`:

### Option A: Local Console Mode (No Gmail Password Required)
```env
EMAIL_DELIVERY_MODE=console
```
- In this mode, emails are printed directly into the **terminal where `uvicorn` is running**.
- Perfect for offline development and testing.

### Option B: Real Email Delivery via Gmail SMTP
```env
EMAIL_DELIVERY_MODE=smtp
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_16_digit_app_password
SMTP_FROM_ADDRESS=your_email@gmail.com
SMTP_FROM_NAME=CAMS Attendance System
SMTP_USE_TLS=true
```

> **How to get the 16-character Google App Password:**
> 1. Go to your Google Account Security: `https://myaccount.google.com/security`
> 2. Ensure **2-Step Verification** is turned ON.
> 3. Go to **App passwords**: `https://myaccount.google.com/apppasswords`
> 4. Create an app named `CAMS Attendance` and copy the 16-letter password into `.env`.

---

## 6. Comprehensive API Directory: What Each API Is Used For

Below is the complete reference for every API in the system, detailing **who uses it**, **its core purpose**, **key parameters**, and **automated side effects** (such as policy calculations and email alerts).

### 6.1 Attendance Tracking APIs (`/api/v1/attendance`)

| API Endpoint | HTTP Method | Target User | What It Is Used For | Inputs / Parameters | Automated Actions & Side Effects |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/api/v1/attendance/entry` | `POST` | Employee / Biometric Device | **Clock-In**: Marks employee entry at the start of the workday. | `employee_id`, `entry_time` (`"09:00"` or ISO), optional `date`, `device_id`. | Validates employee is active; prevents double clock-in (returns 409 if session already open); creates active session with status `PRESENT`. |
| `/api/v1/attendance/exit` | `POST` | Employee / Biometric Device | **Clock-Out**: Marks employee exit when leaving the office. | `employee_id`, `exit_time` (`"12:00"` or ISO), optional `date`, `device_id`. | **CRITICAL TRIGGER**: Matches open session, calculates worked hours. **If total hours < 5.0 hours, instantly dispatches the official Daily Policy Violation Email to the employee.** |
| `/api/v1/attendance/quick-record` | `POST` | Biometric Sync / Tester / HR | **Combined Clock-In & Out**: Records a full workday session in one single call. | `employee_id`, `date`, `entry_time` (`"09:00"`), `exit_time` (`"13:00"`). | Ideal for biometric badge imports. Evaluates session duration: **if < 5.0 hours, automatically triggers the daily violation email alert.** |
| `/api/v1/attendance/{employee_id}` | `GET` | Employee / Manager | **Current Status**: Checks employee's live attendance status for today. | `employee_id` (path parameter). | Returns active clock-in session (if currently in office) or today's completed session history and total cumulative hours. |
| `/api/v1/attendance/{employee_id}/history` | `GET` | Employee / HR Admin | **Attendance Timesheet**: Fetches historical attendance logs over a date range. | `employee_id`, optional `start_date`, `end_date`, `limit`, `skip`. | Returns full chronological session list, entry/exit timestamps, daily durations, and policy status. |
| `/api/v1/attendance/session/{attendance_id}` | `PATCH` | HR Admin (Auth Required) | **Attendance Regularization**: Allows HR to correct clock-in/out times if an employee forgot to badge. | `attendance_id`, `entry_time`, `exit_time`, `attendance_status`, `notes`. | Recalculates session hours and logs an immutable record in `audit_logs` for compliance tracking. |

---

### 6.2 Leave & Holiday Management APIs (`/api/v1/leave` & `/api/v1/holidays`)

| API Endpoint | HTTP Method | Target User | What It Is Used For | Inputs / Parameters | Automated Actions & Side Effects |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/api/v1/leave` | `POST` | Employee (Self-Service) | **Apply for Leave**: Allows employees to request time-off without needing admin credentials. | `employee_id`, `leave_type` (`sick`, `casual`, `annual`, `unpaid`), `start_date`, `end_date`, `reason`. | Validates dates, checks for overlapping pending or approved leaves (rejects with 409 Conflict), sets status to `PENDING`. |
| `/api/v1/leave` | `GET` | HR Admin / Manager | **List Leave Requests**: Lists all employee leave applications. | Optional query filters: `employee_id`, `status` (`pending`, `approved`, `rejected`), date range. | Returns filtered list of leave requests with employee details and submission timestamps. |
| `/api/v1/leave/{leave_id}` | `GET` | Employee / HR Admin | **Leave Details**: Inspects a specific leave application and its review history. | `leave_id` (path parameter). | Returns leave record, applicant details, review timestamp, and reviewer notes. |
| `/api/v1/leave/{leave_id}/approve` | `PATCH` | HR Admin (Auth Required) | **Approve Leave**: Approves an employee's requested time-off. | `leave_id`, optional review `note`. | **POLICY PROTECTION**: Marks leave as `APPROVED`. When weekly audits run, approved leave days automatically scale down required weekly days and hours, safeguarding the employee from wrongful violation notices. |
| `/api/v1/leave/{leave_id}/reject` | `PATCH` | HR Admin (Auth Required) | **Reject Leave**: Rejects an employee's leave application. | `leave_id`, required rejection `reason`. | Updates status to `REJECTED`, records reviewer ID and reason in database. |
| `/api/v1/holidays` | `POST` | HR Admin (Auth Required) | **Declare Company Holiday**: Adds an official holiday to the company calendar. | `name` (e.g. "Labor Day"), `date` (`"YYYY-MM-DD"`), `description`. | Registers holiday in `holidays` collection. Excuses the day from weekly attendance targets. |
| `/api/v1/holidays` | `GET` | All Employees / Admins | **Holiday Calendar**: Lists all upcoming and past company holidays. | Optional `year` query parameter. | Returns array of declared company holidays. |

---

### 6.3 Employee Directory APIs (`/api/v1/employees`)

| API Endpoint | HTTP Method | Target User | What It Is Used For | Inputs / Parameters | Automated Actions & Side Effects |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/api/v1/employees` | `POST` | HR Admin (Auth Required) | **Onboard Employee**: Registers a new employee in the company directory. | `employee_id`, `first_name`, `last_name`, `email`, `department`, `role`. | Ensures `employee_id` and `email` are unique. Creates employee profile and records audit event. |
| `/api/v1/employees` | `GET` | HR Admin (Auth Required) | **Employee Directory**: Searches and lists employees with pagination. | `search` (name, ID, email), `department`, `is_active`, `page`, `page_size`. | Returns paginated list of employees with active status and profile information. |
| `/api/v1/employees/{employee_id}` | `GET` | HR Admin / Manager | **View Profile**: Fetches complete profile of an employee. | `employee_id` (path parameter). | Returns full employee record including department, email, and hire metadata. |
| `/api/v1/employees/{employee_id}` | `PATCH` | HR Admin (Auth Required) | **Update Profile**: Updates employee details (department change, email, role). | `first_name`, `last_name`, `email`, `department`, `role`. | Updates MongoDB document and records administrative changes in `audit_logs`. |
| `/api/v1/employees/{employee_id}` | `DELETE` | HR Admin (Auth Required) | **Offboard Employee**: Deactivates an employee account. | `employee_id` (path parameter). | Performs a safe **soft-delete** (`is_active = false`), preserving all historical timesheets and audit records. |

---

### 6.4 Attendance Reporting & Analytics APIs (`/api/v1/reports`)

| API Endpoint | HTTP Method | Target User | What It Is Used For | Inputs / Parameters | Automated Actions & Side Effects |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/api/v1/reports/attendance` | `GET` | HR Admin / Executives | **Attendance Summary Report**: Aggregates presence data and compliance metrics. | `start_date`, `end_date`, optional `department`, `employee_id`. | Computes total days attended, total hours, average daily hours, and lists all policy violations. |
| `/api/v1/reports/attendance/export.csv` | `GET` | HR / Payroll Administrator | **Export to CSV**: Generates a downloadable spreadsheet of attendance records. | `start_date`, `end_date`, optional `department`. | Returns raw CSV file stream ready for import into Excel, Google Sheets, or payroll software. |

---

### 6.5 Authentication & Admin Security APIs (`/api/v1/auth` & `/api/v1/admin`)

| API Endpoint | HTTP Method | Target User | What It Is Used For | Inputs / Parameters | Automated Actions & Side Effects |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/api/v1/auth/login` | `POST` | Administrators | **Admin Authentication**: Authenticates admin users and issues JWT access tokens. | `username`, `password`. | Verifies Argon2 password hash; returns signed JWT Bearer token valid for 24 hours. |
| `/api/v1/auth/me` | `GET` | Authenticated Admin | **Identity Check**: Returns profile of currently logged-in administrator. | Bearer JWT token in `Authorization` header. | Returns username, email, administrative role, and permissions. |
| `/api/v1/admin/users` | `POST` | Super Administrator | **Create Admin User**: Adds an additional administrator or manager account. | `username`, `email`, `password`, `role`. | Hashes password with Argon2 and stores account in `admin_users`. |
| `/api/v1/admin/users` | `GET` | Super Administrator | **List Admins**: Lists all administrative users in the system. | Pagination parameters. | Returns list of admin accounts and assigned roles. |
| `/api/v1/admin/audit-logs` | `GET` | Compliance / Auditors | **Security Audit Trail**: Inspects immutable audit records of all system actions. | Optional `action`, `resource_type`, `start_date`, `end_date`. | Returns chronological trail of who modified employees, approved leaves, or ran audits. |
| `/api/v1/admin/monitoring/run` | `POST` | HR Admin / Cron Task | **Trigger Weekly Compliance Audit**: Evaluates all employees against weekly policy (3 days, 15 hrs, 5 hrs/day avg). | `target_week_start`, `include_current_week` (`true`/`false`), `force_resend`. | Runs policy engine across all staff, factors in approved leaves/holidays, and dispatches weekly violation emails. |

---

### 6.6 System Health & Observability APIs (`/health`)

| API Endpoint | HTTP Method | Target User | What It Is Used For | Inputs / Parameters | Automated Actions & Side Effects |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/health/live` | `GET` | Docker / Kubernetes / DevOps | **Liveness Probe**: Verifies that the FastAPI application is alive and accepting traffic. | None. | Returns `{"status": "live", "timestamp": "..."}`. |
| `/health/ready` | `GET` | Docker / Kubernetes / DevOps | **Readiness Probe**: Verifies that the application can actively communicate with MongoDB. | None. | Pings MongoDB cluster; returns 200 OK if healthy or 503 Service Unavailable if database is unreachable. |

---

## 7. How to Run and Test in Swagger UI

### Step 1: Start the Backend Server
In PowerShell:
```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Open your browser to: **`http://localhost:8000/docs`**

---

### Step 2: Login as Admin
1. Go to **`POST /api/v1/auth/login`**.
2. Click **Try it out** and submit:
   ```json
   {
     "username": "admin",
     "password": "Admin@123456"
   }
   ```
3. Copy the `access_token` from the response.
4. Click the green **Authorize** button at the top right of the Swagger page, paste the token, and click **Authorize**.

---

### Step 3: Create an Employee
Go to **`POST /api/v1/employees`**:
```json
{
  "employee_id": "EMP-007",
  "name": "Vishrutha",
  "email": "vishrutha7104@gmail.com",
  "department": "Engineering",
  "role": "Software Engineer"
}
```

---

### Step 4: Test Login at 9:00 and Exit Before 5 Hours (< 5 hrs)
1. **Clock In at 09:00**:
   Call **`POST /api/v1/attendance/entry`**:
   ```json
   {
     "employee_id": "EMP-007",
     "entry_time": "09:00"
   }
   ```
2. **Clock Out at 12:00 (Only 3 hours)**:
   Call **`POST /api/v1/attendance/exit`**:
   ```json
   {
     "employee_id": "EMP-007",
     "exit_time": "12:00"
   }
   ```
3. **Immediate Result**:
   - The session is saved with `total_hours: 3.0` and status `complete`.
   - The response returns:
     `"policy_alert": "Policy non-compliance: 3.00 hrs is less than mandatory 5.0 hrs/day. Automated alert email dispatched to vishrutha7104@gmail.com."`
   - Check your Gmail inbox — the professional alert email arrives immediately!

---

### Step 5: Test Single-Click "Quick Record"
Go to **`POST /api/v1/attendance/quick-record`**:
```json
{
  "employee_id": "EMP-007",
  "date": "2026-10-09",
  "entry_time": "09:00",
  "exit_time": "11:30"
}
```
*(Records both entry and exit in one click and checks policy compliance automatically).*

---

### Step 6: Test Employee Self-Service Leave
1. **Submit Leave** (`POST /api/v1/leave`):
   ```json
   {
     "employee_id": "EMP-007",
     "leave_type": "sick",
     "start_date": "2026-10-12",
     "end_date": "2026-10-13",
     "reason": "Doctor appointment and recovery"
   }
   ```
2. **Approve Leave** (`PATCH /api/v1/leave/{leave_id}/approve`):
   Submit with note `{"note": "Approved by manager"}`.
   These dates are now marked as excused in CAMS.

---

### Step 7: Trigger Weekly Monitoring On-Demand
Go to **`POST /api/v1/admin/monitoring/run`**:
- `include_current_week`: `true`
- `force_resend`: `true`
- Click **Execute**.
- Returns complete audit statistics and violation breakdowns across all employees.

---

## 8. MongoDB Database Collections

All collections enforce strict data isolation via a composite index prepending `tenant_id`:

| Collection | Description | Key Fields & Composite Unique Indexes |
| :--- | :--- | :--- |
| `tenants` | Tenant Organizations | `tenant_id` (Unique), `name`, `contact_email`, `settings`, `is_active` |
| `employees` | Registered workforce | Compound index: `(tenant_id, employee_id)` (Unique), `(tenant_id, email)` (Unique) |
| `attendance` | Work session records | Compound index: `(tenant_id, employee_id, date)` |
| `leave_requests`| Employee leave requests | Compound index: `(tenant_id, employee_id, start_date)` |
| `leave_balances`| Annual leave quotas | Compound index: `(tenant_id, employee_id, year, leave_type)` (Unique) |
| `regularization_requests`| Timesheet corrections | Compound index: `(tenant_id, employee_id, date)` |
| `holidays` | Company holidays | Compound index: `(tenant_id, date)` (Unique) |
| `notification_logs`| Email delivery audit | Compound index: `(tenant_id, dedup_key)` (Unique) |
| `audit_logs` | Immutable security trail | Compound index: `(tenant_id, timestamp)` |
| `admin_users` | Admin & manager logins | Compound index: `(tenant_id, username)` (Unique) |

---

## 9. Multi-Tenancy Architecture (Shared Database Model)

### Tenant Isolation & Resolution
- **Tenant Context (`ContextVar`)**: The active tenant is tracked request-scoped via `app/core/tenant.py`.
- **Resolution Strategy**:
  1. `X-Tenant-ID` HTTP header (takes precedence for API clients / frontend).
  2. JWT `tenant_id` claim if authenticated.
  3. Default fallback: `"default"` (ensuring full backward compatibility).
- **Tenant Onboarding (Controlled Admin Provisioning - Option 2)**:
  - Restricted to administrators via `require_admin`.
  - Endpoint: `POST /api/v1/tenants`
  - In a single atomic step, provisions the organization (`tenant_id`, `name`, `contact_email`, customized policy thresholds like `min_days_per_week`, `min_hours_per_week`, `daily_min_average_hours`) and creates the initial organization administrator credentials.
- **Cross-Tenant Worker Monitoring**:
  - The APScheduler worker runs `run_all_tenants_monitoring_cycle()` which iterates each active tenant in the database, scopes repositories to that tenant, and applies that tenant's custom policy thresholds.

---

## 10. Quality Assurance & Tests

The project includes **55 automated tests** covering security, token authentication, API endpoints, deterministic policy math, multi-tenancy data isolation, cross-tenant leak prevention, and automated email dispatching.

To run the test suite:
```powershell
pytest -v
```
To run the code linter:
```powershell
ruff check app/ tests/ scripts/
```
Both commands pass cleanly with **0 errors**.
