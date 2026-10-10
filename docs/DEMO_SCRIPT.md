# Central Attendance Management System (CAMS) — Live Demo Script & Presentation Guide

> **Target Audience**: Technical Interviewers, Project Evaluators, Clients, or Internal Stakeholders  
> **Estimated Presentation Duration**: 8 to 12 minutes  
> **Swagger Documentation**: `http://localhost:8000/docs`  
> **Live Email Demo**: Gmail Inbox showing instant alert  

---

## 📋 Pre-Demo Checklist (Prepare 5 Minutes Before)

1. [ ] **MongoDB is running**: Local MongoDB service on `mongodb://localhost:27017`
2. [ ] **FastAPI Server is running**:
   ```powershell
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
3. [ ] **Open Browser Tabs**:
   - Tab 1: `http://localhost:8000/docs` (Interactive Swagger UI)
   - Tab 2: Your Gmail Inbox (`vishrutha7104@gmail.com`) ready to show the email landing in real-time.
   - Tab 3: VS Code showing the file tree.

---

## 🎙️ Phase 1: Introduction & The Problem Statement (1 - 2 mins)

### 🗣️ What to Say (Word-for-Word):
> *"Good morning / afternoon everyone.*
> 
> *Today, I am presenting the **Central Attendance Management System (CAMS)** — an enterprise-grade backend service built with Python 3.12, FastAPI, and asynchronous MongoDB.*
> 
> *Modern hybrid work environments require transparent, deterministic attendance policies. In many organizations, companies mandate that employees attend office at least **3 days a week**, complete a minimum of **15 hours per week**, and maintain at least a **5-hour daily presence**.*
> 
> *However, traditional HR systems only detect attendance shortfalls at the end of the month when payroll runs. By then, it's too late.*
> 
> *Our system solves this with **instant, real-time policy enforcement**:*
> *1. If an employee logs in and exits before completing the mandatory 5.0 hours, our backend detects the deficit **the exact minute they clock out** and dispatches a branded, executive-level alert email immediately.*
> *2. At the end of the week, an automated auditor evaluates the 3 days / 15 hours requirement.*
> *3. And importantly, our system features a **smart leave adjustment engine**: when an employee takes an approved leave or on company holidays, their weekly target is automatically reduced so excused employees never receive false violation alerts.*
> 
> *Let's take a quick look at the codebase architecture, and then I will demonstrate the live flow with real email delivery."*

---

## 🗂️ Phase 2: Project Architecture & Codebase Walkthrough (2 - 3 mins)

### 🖥️ Action:
Open **VS Code** with the project folder expanded in the explorer tree.

### 🗣️ What to Say:
> *"The project follows a clean, 3-tier enterprise architecture separating HTTP routes, business logic, and database persistence:*
> 
> 1. *`app/main.py`: This is the FastAPI entrypoint. We use the modern `lifespan` context manager to manage database connection pools gracefully and ensure indexes are automatically created on startup.*
> 
> 2. *`app/api/v1/`: Contains all our RESTful routers:*
>    - *`attendance.py`: Endpoints for clock-in (`/entry`), clock-out (`/exit`), and single-click combined sessions (`/quick-record`).*
>    - *`leave.py`: Allows employees to submit leave requests without needing admin credentials, and provides admin endpoints for approvals and rejections.*
>    - *`employees.py`: Full employee lifecycle CRUD operations.*
>    - *`reports.py`: Attendance reporting with clean, downloadable CSV export.*
> 
> 3. *`app/services/`: This is where the core business rules live:*
>    - *`attendance_service.py`: Computes session durations and immediately evaluates the 5-hour daily threshold during clock-out.*
>    - *`policy_service.py`: The deterministic rules engine that audits the 3-day / 15-hour rules and scales thresholds down for approved leaves.*
>    - *`notification_service.py`: Dispatches multi-part MIME emails with responsive corporate HTML styling and plain text fallback.*
> 
> 4. *`app/templates/`: Houses `daily_violation.html` and `weekly_violation.html` — designed like an executive corporate advisory.*
> 
> 5. *`app/database/`: We do not use slow ORMs or deprecated drivers like Motor. We use the official, modern **`AsyncMongoClient`** from PyMongo Async for non-blocking I/O.*
> 
> 6. *`tests/`: The system is thoroughly validated with **39 automated tests** covering security, token authentication, and email triggers with 100% pass rate."*

---

## ⚙️ Phase 3: How to Configure & Explain Gmail SMTP (1 - 2 mins)

### 🖥️ Action:
Show the `.env` file on screen (mask the actual password or show the keys).

### 🗣️ What to Say:
> *"To ensure emails reach real corporate inboxes reliably, we configured SMTP using Gmail's secure relay.*
> 
> *Here is how we set it up:*
> 1. *In `.env`, we set `EMAIL_DELIVERY_MODE=smtp`.*
> 2. *We point to `smtp.gmail.com` on port `587` with TLS enabled (`SMTP_USE_TLS=true`).*
> 3. *For security, Google blocks normal account passwords. Instead, we generate a dedicated **16-digit Google App Password**:*
>    - *We go to `myaccount.google.com/security`.*
>    - *Ensure 2-Step Verification is active.*
>    - *Under 'App Passwords', we generate an app-specific password called `CAMS Attendance` and set it in `.env`.*
> 
> *Now, let me demonstrate the live system in action."*

---

## 🚀 Phase 4: Live Interactive Swagger & Email Demo (4 - 5 mins)

### 🖥️ Action:
Switch browser to **`http://localhost:8000/docs`**.

---

### Step 1: Admin Authentication
> *"First, let's authenticate as an HR Administrator to obtain our JWT Bearer token."*
1. Scroll to **`POST /api/v1/auth/login`**.
2. Click **Try it out**.
3. Use:
   ```json
   {
     "username": "admin",
     "password": "Admin@123456"
   }
   ```
4. Click **Execute**. Show the returned `access_token`.
5. Copy the token. Click the green **Authorize** button at the top right of Swagger, paste it in, and click **Authorize**.

---

### Step 2: Employee Creation / Verification
> *"Next, we register our employee with their official email address."*
1. Scroll to **`POST /api/v1/employees`**.
2. Click **Try it out** and execute:
   ```json
   {
     "employee_id": "EMP-007",
     "name": "Vishrutha",
     "email": "vishrutha7104@gmail.com",
     "department": "Engineering",
     "role": "Software Engineer"
   }
   ```
*(If already registered, mention that `EMP-007` is active in the database).*

---

### Step 3: THE SHOWSTOPPER — Clock-In at 9:00 AM & Exit Under 5 Hours
> *"Now, let's demonstrate the core requirement:*
> *An employee clocks in at 09:00 AM. They are required to stay at least 5.0 hours. But what happens if they exit after only 3.0 hours at 12:00 PM?"*

1. **Clock In**:
   - Go to **`POST /api/v1/attendance/entry`**.
   - Input:
     ```json
     {
       "employee_id": "EMP-007",
       "entry_time": "09:00"
     }
     ```
   - Click **Execute**.
   - Point out to the audience: *"Status is now `incomplete`, session is recorded at 09:00 AM."*

2. **Clock Out with Deficit**:
   - Go to **`POST /api/v1/attendance/exit`**.
   - Input:
     ```json
     {
       "employee_id": "EMP-007",
       "exit_time": "12:00"
     }
     ```
   - Click **Execute**.

3. **Highlight the Response**:
   - Point to the JSON output on screen:
     ```json
     "total_hours": 3.0,
     "attendance_status": "complete",
     "policy_alert": "Policy non-compliance: 3.00 hrs is less than mandatory 5.0 hrs/day. Automated alert email dispatched to vishrutha7104@gmail.com."
     ```
   - Say: *"Notice that the system instantly calculated a duration of 3.0 hours, detected a 2.0-hour shortfall against the mandatory 5.0 hours, and dispatched the email alert the exact second they exited."*

4. **Show Real Email in Gmail**:
   - Switch to your **Gmail Inbox** tab.
   - Open the new email received from `CAMS Attendance System`.
   - Point out the details:
     - Corporate branding header.
     - **Employee Name**: Vishrutha | **ID**: `EMP-007` | **Department**: Engineering.
     - **Hours Logged**: `3.00 hrs` vs **Required**: `5.00 hrs`.
     - **Shortfall Badge**: `2.00 hrs deficit`.
     - 12-hour timestamps: `09:00 AM` to `12:00 PM`.

---

### Step 4: Employee Self-Service Leave & Automatic Protection
> *"Next, what happens if an employee has a legitimate reason to be absent? Can they request a leave without needing administrator credentials?"*

1. Scroll to **`POST /api/v1/leave`**.
2. Point out: *"This endpoint is open to employees without requiring admin tokens."*
3. Execute:
   ```json
   {
     "employee_id": "EMP-007",
     "leave_type": "sick",
     "start_date": "2026-10-12",
     "end_date": "2026-10-13",
     "reason": "Doctor appointment and recovery"
   }
   ```
4. Show the returned `leave_id`.
5. Now go to **`PATCH /api/v1/leave/{leave_id}/approve`** (Admin protected) and approve it.
6. Explain: *"When the weekly compliance audit runs, the policy service detects these 2 approved leave days and automatically scales down the weekly target from 3 days / 15 hours to 2 days / 9 hours. This prevents false violation emails from ever being sent."*

---

### Step 5: On-Demand Weekly Policy Monitoring
> *"Finally, let's run the weekly audit cycle that evaluates the 3 days a week and 15 hours per week policy."*
1. Go to **`POST /api/v1/admin/monitoring/run`**.
2. Set:
   - `include_current_week`: `true`
   - `force_resend`: `true`
3. Click **Execute**.
4. Show the summary:
   - Evaluated employees count.
   - Compliance status.
   - Shortfall reasons.

---

## 🎯 Phase 5: Conclusion & Summary (1 min)

### 🗣️ What to Say:
> *"To summarize:*
> 1. *We built an enterprise-grade solution that enforces both daily (5 hrs) and weekly (3 days / 15 hrs) policies.*
> 2. *Alerts are completely automated and real-time — the employee receives an official email the exact minute they clock out short of 5 hours.*
> 3. *Leaves and holidays are intelligently accounted for to protect compliant employees.*
> 4. *The entire system is backed by modern asynchronous Python, robust error handling, and 39 automated tests.*
> 
> *Thank you, and I would love to answer any questions!"*

---

## 💡 Q&A Cheatsheet (Common Questions & Winning Answers)

| Question | Winning Answer |
| :--- | :--- |
| **Q: Why PyMongo Async instead of Motor or SQLAlchemy?** | *"Motor has known deprecation warnings in newer Python releases. Official PyMongo Async (`AsyncMongoClient`) provides native, zero-overhead asynchronous MongoDB drivers without unnecessary ORM layer abstractions."* |
| **Q: What happens if an employee clocks in and out multiple times a day?** | *"CAMS sums all completed sessions on that date. As long as cumulative active hours reach 5.0 hours, they are marked fully compliant."* |
| **Q: How are duplicate emails prevented if the audit runs multiple times?** | *"We use an idempotent deduplication key in `notification_logs` formatted as `{employee_id}::{week_start}::violation`. If an alert was already delivered for that period, it skips duplicate sends."* |
| **Q: Can this integrate with physical biometric turnstiles?** | *"Yes! Biometric devices can call `POST /api/v1/attendance/entry` and `POST /api/v1/attendance/exit` on badge scan, or batch sync historical punches via `POST /api/v1/attendance/quick-record`."* |
