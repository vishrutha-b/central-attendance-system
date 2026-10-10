import os
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

def set_cell_background(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)

def add_header(doc, text, level):
    p = doc.add_heading(text, level=level)
    run = p.runs[0]
    if level == 1:
        run.font.size = Pt(16)
        run.font.color.rgb = RGBColor(15, 23, 42)
        run.font.bold = True
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(4)
    elif level == 2:
        run.font.size = Pt(13)
        run.font.color.rgb = RGBColor(30, 41, 59)
        run.font.bold = True
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(3)
    elif level == 3:
        run.font.size = Pt(11)
        run.font.color.rgb = RGBColor(71, 85, 105)
        run.font.bold = True
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(2)
    return p

def add_callout(doc, text, title=None, alert_type="note"):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    cell = tbl.cell(0, 0)
    cell.width = Inches(6.5)
    
    bg = "F8FAFC"
    border = "3B82F6"
    if alert_type == "speaker":
        bg = "F0FDF4"
        border = "10B981"
    elif alert_type == "action":
        bg = "FFFBEB"
        border = "F59E0B"
    elif alert_type == "code":
        bg = "F1F5F9"
        border = "64748B"
        
    set_cell_background(cell, bg)
    set_cell_margins(cell, top=100, bottom=100, left=150, right=120)
    
    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:top w:val="none"/>'
        f'<w:left w:val="single" w:sz="24" w:space="0" w:color="{border}"/>'
        f'<w:bottom w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'</w:tcBorders>'
    )
    tcPr.append(borders)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    if title:
        rt = p.add_run(f"{title}\n")
        rt.bold = True
        rt.font.size = Pt(10)
        rt.font.color.rgb = RGBColor(15, 23, 42)
    rt2 = p.add_run(text)
    rt2.font.size = Pt(9.5)
    rt2.font.italic = (alert_type == "speaker")
    rt2.font.color.rgb = RGBColor(30, 41, 59)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)

def build_1_hour_docx(out_path):
    doc = Document()
    for s in doc.sections:
        s.top_margin = Inches(0.8)
        s.bottom_margin = Inches(0.8)
        s.left_margin = Inches(0.8)
        s.right_margin = Inches(0.8)
        
    p_t = doc.add_paragraph()
    p_t.paragraph_format.space_before = Pt(10)
    p_t.paragraph_format.space_after = Pt(2)
    r_t = p_t.add_run("Central Attendance Management System (CAMS)")
    r_t.font.size = Pt(22)
    r_t.font.bold = True
    r_t.font.color.rgb = RGBColor(15, 23, 42)
    
    p_s = doc.add_paragraph()
    p_s.paragraph_format.space_after = Pt(10)
    r_s = p_s.add_run("60-Minute Master Presentation & Technical Deep-Dive Guide")
    r_s.font.size = Pt(13)
    r_s.font.color.rgb = RGBColor(100, 116, 139)
    
    add_callout(
        doc,
        "Session Type: Comprehensive Technical Presentation, Architecture Review & Live Product Demo\n"
        "Total Duration: 60 Minutes (Full Master Edition)\n"
        "Live Swagger URL: http://localhost:8000/docs\n"
        "Live Email Demo: Real Gmail Delivery (Instant 5-Hour Exit Alert to vishrutha7104@gmail.com)\n"
        "Database: MongoDB 7.0 (cams_dev)",
        title="SESSION METADATA",
        alert_type="note"
    )
    
    # Timeline Table
    add_header(doc, "Master Agenda & Timeline (60 Minutes)", level=1)
    timeline_rows = [
        ["Segment", "Time Allocation", "Topic", "Focus Area"],
        ["Module 1", "00:00 – 08:00 (8 mins)", "Executive Introduction & Problem", "Hybrid policy challenges, 3 days/15 hrs/5 hrs rule, real-time vs monthly audits."],
        ["Module 2", "08:00 – 18:00 (10 mins)", "System Architecture & Tech Choices", "FastAPI + Python 3.12, PyMongo Async, MongoDB collections, indexing strategy."],
        ["Module 3", "18:00 – 28:00 (10 mins)", "Codebase Deep Dive & Clean Arch", "Lifespan, IoC & DI, Pydantic validators, duration math, leave scaling algorithm."],
        ["Module 4", "28:00 – 36:00 (8 mins)", "Enterprise Email Engine & SMTP", "Console vs SMTP, Google App Passwords, STARTTLS port 587, HTML templates."],
        ["Module 5", "36:00 – 48:00 (12 mins)", "Live Hands-On Interactive Demo", "Admin auth, Employee onboarding, Instant Exit Email (<5h), Leave workflows, Audit."],
        ["Module 6", "48:00 – 54:00 (6 mins)", "Testing, Code Quality & Reliability", "39 automated async tests, Ruff linting, deduplication mechanisms, soft-deletes."],
        ["Module 7", "54:00 – 60:00 (6 mins)", "Q&A, Scalability & Production Roadmap", "IoT turnstile integration, horizontal scaling, Celery/Redis queues, GDPR compliance."]
    ]
    tbl_t = doc.add_table(rows=len(timeline_rows), cols=4)
    tbl_t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_widths = [Inches(1.2), Inches(1.8), Inches(1.8), Inches(2.2)]
    for r_idx, row in enumerate(timeline_rows):
        for c_idx, val in enumerate(row):
            c = tbl_t.cell(r_idx, c_idx)
            c.width = t_widths[c_idx]
            set_cell_margins(c, top=60, bottom=60, left=80, right=80)
            p = c.paragraphs[0]
            r = p.add_run(val)
            if r_idx == 0:
                set_cell_background(c, "1E293B")
                r.bold = True
                r.font.size = Pt(9)
                r.font.color.rgb = RGBColor(255, 255, 255)
            else:
                set_cell_background(c, "F8FAFC" if r_idx % 2 == 1 else "FFFFFF")
                r.font.size = Pt(8.5)
                r.font.color.rgb = RGBColor(30, 41, 59)
                
    doc.add_paragraph().paragraph_format.space_after = Pt(4)
    
    # Module 1
    add_header(doc, "Module 1: Executive Introduction & Business Problem (00:00 – 08:00)", level=1)
    add_callout(
        doc,
        '"Good morning / afternoon everyone. Welcome to today’s technical deep-dive and live demonstration of the Central Attendance Management System (CAMS).\n\n'
        'Over the next 60 minutes, we will walk through the business challenges modern enterprises face with hybrid attendance, review our architectural decisions, inspect the underlying codebase, configure real enterprise SMTP, run a live end-to-end demonstration with real email alerts, and explore our automated test suite and production scalability roadmap.\n\n'
        'The Core Business Problem:\n'
        'In today’s corporate environment, companies worldwide have transitioned to hybrid work models. At our organization, leadership established a clear, unambiguous office attendance policy:\n'
        '1. Every employee must attend the office at least 3 days per week.\n'
        '2. Every employee must accumulate a minimum of 15 hours per week.\n'
        '3. Across attended days, employees must maintain a daily presence of at least 5.0 hours per day.\n\n'
        'Why Traditional Systems Fail:\n'
        'Most legacy HR systems and biometric integrations operate on a delayed monthly batch cycle. At the end of the month, an administrator pulls a CSV export, runs spreadsheet macros, and flags employees who missed their quota. By then, it is 30 days too late.\n\n'
        'How CAMS Solves This:\n'
        'CAMS introduces real-time, event-driven policy enforcement:\n'
        '• Instant Exit Alerts: When an employee clocks in at 9:00 AM and exits at 12:00 PM—having completed only 3.0 hours instead of the mandatory 5.0 hours—our backend detects this shortfall the exact second they clock out. The system immediately dispatches an official corporate policy alert to that employee’s inbox.\n'
        '• Weekly Deterministic Audits: At week close, a scheduler audits the 3 days / 15 hours requirement.\n'
        '• Smart Leave & Holiday Scaling: If an employee takes an approved leave or on official holidays, the weekly quota is dynamically scaled down, preventing false penalties."',
        title="SPEAKER SCRIPT — WHAT TO SAY",
        alert_type="speaker"
    )
    
    # Module 2
    add_header(doc, "Module 2: System Architecture & Technology Choices (08:00 – 18:00)", level=1)
    add_callout(
        doc,
        '"When designing CAMS, our guiding engineering principles were high concurrency, sub-millisecond response times, zero blocking I/O, and strict type safety.\n\n'
        '1. Python 3.12 + FastAPI:\n'
        'Built on Starlette and Pydantic v2, providing native asynchronous execution (async/await), automatic Swagger UI generation, and lightning-fast request validation.\n\n'
        '2. The Database Layer: Why PyMongo Async (AsyncMongoClient)?\n'
        'Many legacy Python MongoDB tutorials rely on Motor. However, Motor has known deprecation warnings in modern Python 3.11+ runtimes and relies on wrapping the synchronous driver in threadpools. In CAMS, we use the official native AsyncMongoClient from PyMongo Async for direct event-loop integration, true connection pooling, and zero ORM overhead.\n\n'
        '3. The 7 MongoDB Collections:\n'
        '• employees (Workforce directory)\n'
        '• attendance (Work sessions)\n'
        '• leave_requests (Leave applications & approvals)\n'
        '• holidays (Company holidays calendar)\n'
        '• notification_logs (Email delivery audit trail & deduplication)\n'
        '• audit_logs (Security and admin actions)\n'
        '• admin_users (Hashed administrative accounts)\n\n'
        '4. Compound Indexing Strategy (indexes.py):\n'
        'We provision compound indexes on attendance (employee_id, date, exit_time) and unique indexes on employee_id and email to ensure sub-millisecond lookups even across millions of records."',
        title="SPEAKER SCRIPT — WHAT TO SAY",
        alert_type="speaker"
    )
    
    # Module 3 (DEEP CODEBASE DIVE)
    add_header(doc, "Module 3: Codebase Deep Dive & Clean Architecture (18:00 – 28:00)", level=1)
    add_callout(doc, "Action: Show the VS Code folder structure: app/main.py, app/api/dependencies.py, app/schemas/attendance.py, app/services/attendance_service.py, app/services/policy_service.py.", title="PRESENTER ACTION", alert_type="action")
    add_callout(
        doc,
        '"Now, let us examine the engineering heart of CAMS. The repository strictly implements Clean 3-Tier Enterprise Architecture: separating Presentation, Business Logic, and Data Access, tied together by Dependency Injection and Pydantic v2 schemas.\n\n'
        '1. Application Lifecycle & Lifespan Context Manager (app/main.py):\n'
        'Rather than deprecated startup/shutdown events, we implemented the modern asynccontextmanager Lifespan handler. This guarantees that database connection pools and compound indexes are provisioned before accepting any HTTP requests, and safely flushes sockets on SIGTERM without dropping queries.\n\n'
        '2. Inversion of Control & Dependency Injection (app/api/dependencies.py):\n'
        'Our routers never instantiate repositories directly. We use FastAPI\'s Depends() to inject AttendanceRepository, EmployeeRepository, and NotificationService. We engineered dual-access dependencies: require_admin() strictly protects management routes, while get_optional_current_admin() allows employees to submit self-service leave requests freely.\n\n'
        '3. Pydantic v2 Schema Modeling & Flexible Time Parsing (app/schemas/attendance.py):\n'
        'We built custom @field_validator("entry_time", mode="before") parsers. It seamlessly accepts simple 24-hour time strings ("09:00", "12:30") from Swagger/mobile apps as well as full ISO-8601 strings from biometric hardware, dynamically normalizing them into timezone-aware UTC datetime objects.\n\n'
        '4. Attendance Calculation Engine & Instant Violation Trigger (app/services/attendance_service.py):\n'
        '• Prevents double clock-in by querying open sessions (exit_time = None) and raising 409 Conflict.\n'
        '• Computes exact duration: duration = round((exit_time - entry_time).total_seconds() / 3600, 2).\n'
        '• Aggregates multiple daily sessions for employees who leave for lunch.\n'
        '• THE INSTANT TRIGGER: Inside record_exit(), if total daily hours < 5.0, it immediately calls notification_service.send_daily_violation_email(). No cron delay—the alert email lands the exact second they exit.\n\n'
        '5. Deterministic Policy Engine & Dynamic Leave Scaling (app/services/policy_service.py):\n'
        'Audits the 3 days / 15 hrs / 5 hrs rules. When an employee takes approved leaves or on holidays, the algorithm calculates net working days: net_days = 5 - (leaves + holidays). It proportionally scales down required days using ceiling math (ceil(3 * net_days / 5)) and hours (round(15 * net_days / 5, 2)), mathematically guaranteeing zero false penalties.\n\n'
        '6. Direct PyMongo Async Operations & Atomic Updates (app/repositories/):\n'
        'Executes raw async queries using atomic MongoDB $set operators for single-document transactional integrity, resolving in sub-millisecond time via compound B-tree indexes.\n\n'
        '7. Enterprise Security & Argon2id Hashing (app/security/):\n'
        'Uses Argon2id via pwdlib—the OWASP recommended memory-hard hashing algorithm resistant to GPU/ASIC attacks, paired with HMAC-SHA256 signed JWT tokens and immutable audit logs."',
        title="SPEAKER SCRIPT — WHAT TO SAY (IMPRESS YOUR EVALUATOR)",
        alert_type="speaker"
    )
    
    # Module 4
    add_header(doc, "Module 4: Enterprise Email Engine & SMTP Setup (28:00 – 36:00)", level=1)
    add_callout(
        doc,
        '"In .env, we support two modes: EMAIL_DELIVERY_MODE=console for offline development, and EMAIL_DELIVERY_MODE=smtp for production email delivery.\n\n'
        'How to explain Google App Passwords:\n'
        '1. We point to smtp.gmail.com on Port 587 with STARTTLS encryption enabled (SMTP_USE_TLS=true).\n'
        '2. Google blocks basic password authentication for security.\n'
        '3. We enable 2-Step Verification on the Google account and generate a dedicated 16-character Google App Password for CAMS Attendance.\n'
        '4. This grants secure SMTP relay access without exposing personal account credentials.\n\n'
        'Multipart MIME Design:\n'
        'Emails are delivered via MIMEMultipart("alternative"), attaching both rich responsive HTML (with corporate headers, status badges, and deficit metrics) and a clean plain text fallback."',
        title="SPEAKER SCRIPT — WHAT TO SAY",
        alert_type="speaker"
    )
    
    # Module 5
    add_header(doc, "Module 5: Live Hands-On Interactive Demonstration (36:00 – 48:00)", level=1)
    add_callout(doc, "Action: Switch to Swagger UI at http://localhost:8000/docs with Gmail open in side tab.", title="PRESENTER ACTION", alert_type="action")
    
    demo_steps = [
        ("Step 1: Admin Authentication", "Execute POST /api/v1/auth/login with admin / Admin@123456. Copy token and authorize Swagger."),
        ("Step 2: Employee Profile Check", "Execute GET /api/v1/employees/EMP-007. Show active employee Vishrutha (vishrutha7104@gmail.com)."),
        ("Step 3: THE SHOWSTOPPER — Login at 9:00 AM, Exit at 12:00 PM (< 5 Hours)",
         "1. Clock-in: POST /api/v1/attendance/entry with entry_time='09:00'. Show session recorded as incomplete.\n"
         "2. Clock-out: POST /api/v1/attendance/exit with exit_time='12:00'.\n"
         "3. Highlight JSON output: total_hours = 3.0, policy_alert triggered.\n"
         "4. Switch live to Gmail Inbox: Show the arriving email with corporate branding, 3.0h completed, 5.0h required, and 2.0h deficit badge!"),
        ("Step 4: Self-Service Leave & Dynamic Threshold Scaling",
         "1. Submit leave via POST /api/v1/leave (no admin token required).\n"
         "2. Approve leave via PATCH /api/v1/leave/{id}/approve.\n"
         "3. Explain that approved leave days dynamically lower required weekly days & hours, protecting excused staff."),
        ("Step 5: On-Demand Weekly Audit & CSV Export",
         "1. Execute POST /api/v1/admin/monitoring/run with include_current_week=true.\n"
         "2. Download spreadsheet via GET /api/v1/reports/attendance/export.csv.")
    ]
    for st, sd in demo_steps:
        add_header(doc, st, level=2)
        p = doc.add_paragraph()
        r = p.add_run(sd)
        r.font.size = Pt(9.5)
        
    # Module 6
    add_header(doc, "Module 6: Testing, Code Quality & Reliability (48:00 – 54:00)", level=1)
    add_callout(
        doc,
        '"Enterprise systems require verified reliability.\n\n'
        '1. Automated Test Suite (pytest -v):\n'
        'We have 39 automated asynchronous tests covering authentication, employee lifecycle, instant exit email alerts, leave workflows, and compliance audits — running in ~1.2s with 100% pass rate.\n\n'
        '2. Static Code Analysis (ruff check app tests):\n'
        '0 errors across the entire codebase.\n\n'
        '3. Idempotent Deduplication:\n'
        'Every email notification generates a unique deduplication key ({employee_id}::{week_start}::violation) in notification_logs, guaranteeing that running audits repeatedly never spams employees."',
        title="SPEAKER SCRIPT — WHAT TO SAY",
        alert_type="speaker"
    )
    
    # Module 7
    add_header(doc, "Module 7: Q&A, Scalability & Production Roadmap (54:00 – 60:00)", level=1)
    add_callout(
        doc,
        '"To wrap up before open Q&A, here is how CAMS scales in an enterprise:\n'
        '• Physical IoT Turnstile Integration: Hardware devices call /entry and /exit directly on badge scan using machine API keys.\n'
        '• Horizontal Scaling: FastAPI is stateless and containerized. High-volume background audits can offload to Redis + Celery.\n'
        '• MongoDB Sharding: Sharded on (employee_id, date) partition keys for effortless scaling across millions of records.\n\n'
        'Thank you! I am now delighted to take your questions."',
        title="SPEAKER SCRIPT — WHAT TO SAY",
        alert_type="speaker"
    )
    
    # Q&A Table
    add_header(doc, "Master Q&A Cheatsheet", level=1)
    qa_rows = [
        ["Question", "Winning Senior Technical Answer"],
        ["Why PyMongo Async over Motor?", "Motor wraps sync drivers in threadpools and has deprecation issues in modern Python. PyMongo Async (AsyncMongoClient) provides native event loop integration and sub-millisecond query execution without ORM overhead."],
        ["How are multiple punches handled?", "CAMS sums all completed sessions on that date. As long as cumulative active hours reach 5.0 hours, the employee is fully compliant."],
        ["What if an employee forgets to clock out?", "Open sessions remain incomplete. HR administrators can regularize the session via PATCH /attendance/session/{id}, with all changes recorded in audit_logs."],
        ["How does the leave system prevent fraud?", "leave_repo executes an overlap query checking date ranges against existing requests. Any collision immediately returns 409 Conflict."]
    ]
    tbl_q = doc.add_table(rows=len(qa_rows), cols=2)
    tbl_q.alignment = WD_TABLE_ALIGNMENT.CENTER
    for r_idx, row in enumerate(qa_rows):
        for c_idx, val in enumerate(row):
            c = tbl_q.cell(r_idx, c_idx)
            c.width = [Inches(2.5), Inches(4.0)][c_idx]
            set_cell_margins(c, top=80, bottom=80, left=100, right=100)
            p = c.paragraphs[0]
            r = p.add_run(val)
            if r_idx == 0:
                set_cell_background(c, "1E293B")
                r.bold = True
                r.font.size = Pt(9.5)
                r.font.color.rgb = RGBColor(255, 255, 255)
            else:
                set_cell_background(c, "F8FAFC" if r_idx % 2 == 1 else "FFFFFF")
                r.font.size = Pt(9)
                r.font.color.rgb = RGBColor(30, 41, 59)
                
    doc.save(out_path)
    print(f"Generated 1-Hour Word Document: {out_path}")

def build_1_hour_html(out_path):
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CAMS — 60-Minute Master Presentation & Technical Demo Script</title>
<style>
  :root {
    --primary: #0f172a;
    --accent: #2563eb;
    --accent-light: #eff6ff;
    --success: #16a34a;
    --success-light: #f0fdf4;
    --warning: #f59e0b;
    --warning-light: #fffbeb;
    --border: #e2e8f0;
    --text: #1e293b;
    --text-muted: #64748b;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    background: #f8fafc;
    color: var(--text);
    line-height: 1.6;
    padding: 40px 20px;
  }
  .container {
    max-width: 950px;
    margin: 0 auto;
    background: #ffffff;
    border-radius: 12px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.06);
    border: 1px solid var(--border);
    overflow: hidden;
  }
  .header {
    background: var(--primary);
    color: #ffffff;
    padding: 40px;
    border-bottom: 4px solid var(--accent);
  }
  .badge-tag {
    display: inline-block;
    background: rgba(255,255,255,0.15);
    color: #93c5fd;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    padding: 4px 10px;
    border-radius: 4px;
    margin-bottom: 12px;
  }
  .header h1 { font-size: 28px; font-weight: 800; margin-bottom: 8px; letter-spacing: -0.5px; }
  .header p { color: #94a3b8; font-size: 15px; }
  .content { padding: 40px; }
  h2 {
    font-size: 20px;
    font-weight: 700;
    color: var(--primary);
    border-bottom: 2px solid var(--border);
    padding-bottom: 8px;
    margin: 40px 0 16px 0;
  }
  h2:first-of-type { margin-top: 0; }
  h3 { font-size: 16px; font-weight: 700; color: var(--primary); margin: 24px 0 10px 0; }
  .card-speech {
    background: var(--success-light);
    border-left: 4px solid var(--success);
    padding: 20px;
    border-radius: 0 8px 8px 0;
    margin: 18px 0;
    font-size: 14px;
    font-style: italic;
    color: #14532d;
    line-height: 1.7;
  }
  .card-speech-title {
    font-style: normal;
    font-weight: 700;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #166534;
    margin-bottom: 10px;
  }
  .card-action {
    background: var(--warning-light);
    border-left: 4px solid var(--warning);
    padding: 12px 18px;
    border-radius: 0 8px 8px 0;
    margin: 14px 0;
    font-size: 13.5px;
    color: #78350f;
    font-weight: 600;
  }
  .time-badge {
    background: #e2e8f0;
    color: #334155;
    font-size: 12px;
    font-weight: 700;
    padding: 3px 8px;
    border-radius: 4px;
    margin-right: 8px;
  }
  ul, ol { padding-left: 22px; margin-bottom: 16px; }
  li { margin-bottom: 6px; font-size: 14px; }
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 16px 0 24px 0;
    font-size: 13px;
  }
  th {
    background: var(--primary);
    color: #ffffff;
    text-align: left;
    padding: 11px 14px;
  }
  td {
    padding: 10px 14px;
    border-bottom: 1px solid var(--border);
  }
  tr:nth-child(even) { background: #f8fafc; }
  pre {
    background: #0f172a;
    color: #e2e8f0;
    padding: 14px;
    border-radius: 6px;
    font-size: 13px;
    overflow-x: auto;
    margin: 12px 0;
  }
  code { font-family: Consolas, monospace; }
  @media print {
    body { padding: 0; background: #fff; }
    .container { box-shadow: none; border: none; }
  }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="badge-tag">60-Minute Master Edition</div>
    <h1>Central Attendance Management System (CAMS)</h1>
    <p>Complete Technical Presentation, Architecture Review & Live Product Demo Guide</p>
  </div>
  <div class="content">

    <h2>Master Agenda & Timeline (60 Minutes)</h2>
    <table>
      <thead>
        <tr>
          <th>Segment</th>
          <th>Time Allocation</th>
          <th>Topic</th>
          <th>Focus Area</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>Module 1</strong></td>
          <td><span class="time-badge">00:00 – 08:00</span>(8 mins)</td>
          <td>Executive Introduction & Problem</td>
          <td>Hybrid policy challenges, 3 days/15 hrs/5 hrs rule, real-time vs monthly audits.</td>
        </tr>
        <tr>
          <td><strong>Module 2</strong></td>
          <td><span class="time-badge">08:00 – 18:00</span>(10 mins)</td>
          <td>System Architecture & Tech Choices</td>
          <td>FastAPI + Python 3.12, PyMongo Async, MongoDB collections, indexing strategy.</td>
        </tr>
        <tr>
          <td><strong>Module 3</strong></td>
          <td><span class="time-badge">18:00 – 28:00</span>(10 mins)</td>
          <td>Codebase Deep Dive & Clean Architecture</td>
          <td>Lifespan, IoC & DI, Pydantic validators, duration math, leave scaling algorithm.</td>
        </tr>
        <tr>
          <td><strong>Module 4</strong></td>
          <td><span class="time-badge">28:00 – 36:00</span>(8 mins)</td>
          <td>Enterprise Email Engine & SMTP</td>
          <td>Console vs SMTP, Google App Passwords, STARTTLS port 587, HTML templates.</td>
        </tr>
        <tr>
          <td><strong>Module 5</strong></td>
          <td><span class="time-badge">36:00 – 48:00</span>(12 mins)</td>
          <td>Live Hands-On Interactive Demo</td>
          <td>Admin auth, Employee onboarding, Instant Exit Email (&lt;5h), Leave workflows, Audit.</td>
        </tr>
        <tr>
          <td><strong>Module 6</strong></td>
          <td><span class="time-badge">48:00 – 54:00</span>(6 mins)</td>
          <td>Testing, Code Quality & Reliability</td>
          <td>39 automated async tests, Ruff linting, deduplication mechanisms, soft-deletes.</td>
        </tr>
        <tr>
          <td><strong>Module 7</strong></td>
          <td><span class="time-badge">54:00 – 60:00</span>(6 mins)</td>
          <td>Q&A, Scalability & Production Roadmap</td>
          <td>IoT turnstile integration, horizontal scaling, Celery/Redis queues, GDPR compliance.</td>
        </tr>
      </tbody>
    </table>

    <h2>Pre-Demo Checklist (10 Minutes Prior)</h2>
    <ul>
      <li><strong>MongoDB Running</strong>: Verify <code>mongodb://localhost:27017</code> is active.</li>
      <li><strong>FastAPI Running</strong>: <code>uvicorn app.main:app --reload --host 0.0.0.0 --port 8000</code></li>
      <li><strong>Browser Tabs Ready</strong>:
        <ol>
          <li><code>http://localhost:8000/docs</code> (Swagger UI)</li>
          <li>Gmail Inbox (<code>vishrutha7104@gmail.com</code>) to show live email landing</li>
          <li>VS Code with project folder expanded</li>
        </ol>
      </li>
    </ul>

    <h2>Module 1: Executive Introduction & Business Problem (00:00 – 08:00)</h2>
    <div class="card-speech">
      <div class="card-speech-title">🗣️ Speaker Script — Word-for-Word:</div>
      "Good morning / afternoon everyone. Welcome to today’s technical deep-dive and live demonstration of the Central Attendance Management System (CAMS).<br><br>
      Over the next 60 minutes, we will walk through the business challenges modern enterprises face with hybrid attendance, review our architectural decisions, inspect the underlying codebase, configure real enterprise SMTP, run a live end-to-end demonstration with real email alerts, and explore our automated test suite and production scalability roadmap.<br><br>
      <strong>The Core Business Problem:</strong><br>
      In today’s corporate environment, companies worldwide have transitioned to hybrid work models. At our organization, leadership established a clear, unambiguous office attendance policy:<br>
      1. Every employee must attend the office at least <strong>3 days per week</strong>.<br>
      2. Every employee must accumulate a minimum of <strong>15 hours per week</strong>.<br>
      3. Across attended days, employees must maintain a daily presence of at least <strong>5.0 hours per day</strong>.<br><br>
      <strong>Why Traditional Systems Fail:</strong><br>
      Most legacy HR systems and biometric integrations operate on a <strong>delayed monthly batch cycle</strong>. At the end of the month, an administrator pulls a CSV export, runs spreadsheet macros, and flags employees who missed their quota. By then, it is 30 days too late. The employee had no timely feedback, managers couldn't intervene, and payroll disputes become inevitable.<br><br>
      <strong>How CAMS Solves This:</strong><br>
      CAMS introduces <strong>real-time, event-driven policy enforcement</strong>:<br>
      • <strong>Instant Exit Alerts</strong>: When an employee clocks in at 9:00 AM and exits at 12:00 PM—having completed only 3.0 hours instead of the mandatory 5.0 hours—our backend detects this shortfall <strong>the exact second they clock out</strong>. The system immediately dispatches an official corporate policy alert to that employee’s inbox.<br>
      • <strong>Weekly Deterministic Audits</strong>: At week close, a scheduler audits the 3 days / 15 hours requirement.<br>
      • <strong>Smart Leave & Holiday Scaling</strong>: If an employee takes an approved leave or on official holidays, the weekly quota is dynamically scaled down (e.g., from 3 days / 15 hrs to 2 days / 9 hrs), preventing false penalties."
    </div>

    <h2>Module 2: System Architecture & Technology Choices (08:00 – 18:00)</h2>
    <div class="card-speech">
      <div class="card-speech-title">🗣️ Speaker Script:</div>
      "When designing CAMS, our guiding engineering principles were high concurrency, sub-millisecond response times, zero blocking I/O, and strict type safety.<br><br>
      <strong>1. Python 3.12 + FastAPI:</strong><br>
      FastAPI provides Starlette's asynchronous execution, Pydantic v2's ultra-fast serialization, and automatic Swagger documentation.<br><br>
      <strong>2. Why PyMongo Async (AsyncMongoClient)?</strong><br>
      Motor has known deprecation warnings on Python 3.11+ runtimes and relies on wrapping the synchronous driver. In CAMS, we use the official native <code>AsyncMongoClient</code> from PyMongo Async for native event loop integration and zero ORM overhead.<br><br>
      <strong>3. The 7 MongoDB Collections:</strong><br>
      • <code>employees</code>: Workforce master records<br>
      • <code>attendance</code>: Work session records (entry, exit, duration)<br>
      • <code>leave_requests</code>: Leave applications and review states<br>
      • <code>holidays</code>: Official corporate holiday registry<br>
      • <code>notification_logs</code>: Immutable email audit trail and deduplication<br>
      • <code>audit_logs</code>: Administrative security trail<br>
      • <code>admin_users</code>: Argon2-hashed administrative credentials<br><br>
      <strong>4. Compound Indexing Strategy:</strong><br>
      In <code>indexes.py</code>, we build compound indexes on attendance <code>(employee_id, date)</code> and <code>(employee_id, exit_time)</code>, plus unique indexes on employee IDs and emails, guaranteeing sub-millisecond query performance across millions of rows."
    </div>

    <h2>Module 3: Codebase Deep Dive & Clean Architecture (18:00 – 28:00)</h2>
    <div class="card-action">🖥️ Action: Show the VS Code folder tree: app/main.py, app/api/dependencies.py, app/schemas/attendance.py, app/services/attendance_service.py, app/services/policy_service.py.</div>
    <div class="card-speech">
      <div class="card-speech-title">🗣️ Speaker Script — Technical Mastery Deep Dive:</div>
      "Now, let us examine the engineering heart of CAMS. The repository strictly implements Clean 3-Tier Enterprise Architecture: separating Presentation (Routers), Business Logic (Services), and Data Access (Repositories), tied together by Dependency Injection and strict Pydantic v2 schemas.<br><br>
      <strong>1. Application Lifecycle & Lifespan Context Manager (app/main.py):</strong><br>
      Rather than deprecated startup/shutdown events, we implemented Python 3.12's <code>asynccontextmanager</code> lifespan handler. It connects to the MongoDB connection pool and builds compound indexes idempotently before any HTTP requests are accepted, and flushes sockets cleanly upon shutdown without dropping active queries.<br><br>
      <strong>2. Inversion of Control & Dependency Injection (app/api/dependencies.py):</strong><br>
      Our routers never instantiate repositories directly. We use FastAPI's <code>Depends()</code> to inject AttendanceRepository, EmployeeRepository, and NotificationService. We engineered dual-access dependencies: <code>require_admin()</code> strictly protects management routes, while <code>get_optional_current_admin()</code> allows employees to submit self-service leave requests freely.<br><br>
      <strong>3. Pydantic v2 Schema Modeling & Flexible Time Parsing (app/schemas/attendance.py):</strong><br>
      We built custom <code>@field_validator('entry_time', mode='before')</code> parsers. It seamlessly accepts simple 24-hour time strings ('09:00', '12:30') from Swagger/mobile apps as well as full ISO-8601 strings from biometric hardware, dynamically normalizing them into timezone-aware UTC datetime objects.<br><br>
      <strong>4. Attendance Calculation Engine & Instant Violation Trigger (app/services/attendance_service.py):</strong><br>
      • Prevents double clock-in by querying open sessions (exit_time = None) and raising 409 Conflict.<br>
      • Computes exact duration: <code>duration = round((exit_time - entry_time).total_seconds() / 3600, 2)</code>.<br>
      • Aggregates multiple daily sessions for employees who leave for lunch.<br>
      • <strong>THE INSTANT TRIGGER:</strong> Inside <code>record_exit()</code>, if total daily hours &lt; 5.0, it immediately calls <code>notification_service.send_daily_violation_email()</code>. No cron delay—the alert email lands the exact second they exit.<br><br>
      <strong>5. Deterministic Policy Engine & Dynamic Leave Scaling (app/services/policy_service.py):</strong><br>
      Audits the 3 days / 15 hrs / 5 hrs rules. When an employee takes approved leaves or on holidays, the algorithm calculates net working days: <code>net_days = 5 - (leaves + holidays)</code>. It proportionally scales down required days using ceiling math (<code>ceil(3 * net_days / 5)</code>) and hours (<code>round(15 * net_days / 5, 2)</code>), mathematically guaranteeing zero false penalties.<br><br>
      <strong>6. Direct PyMongo Async Operations & Atomic Updates (app/repositories/):</strong><br>
      Executes raw async queries using atomic MongoDB <code>$set</code> operators for single-document transactional integrity, resolving in sub-millisecond time via compound B-tree indexes.<br><br>
      <strong>7. Enterprise Security & Argon2id Hashing (app/security/):</strong><br>
      Uses Argon2id via <code>pwdlib</code>—the OWASP recommended memory-hard hashing algorithm resistant to GPU/ASIC attacks, paired with HMAC-SHA256 signed JWT tokens and immutable audit logs."
    </div>

    <h2>Module 4: Enterprise Email Engine & SMTP Setup (28:00 – 36:00)</h2>
    <div class="card-speech">
      <div class="card-speech-title">🗣️ Speaker Script:</div>
      "In <code>.env</code>, we support two modes: <code>EMAIL_DELIVERY_MODE=console</code> for local development, and <code>EMAIL_DELIVERY_MODE=smtp</code> for production delivery.<br><br>
      <strong>How Google App Passwords Work:</strong><br>
      1. We point to <code>smtp.gmail.com</code> on Port 587 with STARTTLS encryption.<br>
      2. Google blocks basic password authentication for third-party apps.<br>
      3. We enable 2-Step Verification and generate a dedicated 16-character Google App Password for 'CAMS Attendance'.<br>
      4. This provides TLS transport encryption without exposing personal passwords.<br><br>
      <strong>Multipart MIME Design:</strong><br>
      Emails are delivered via <code>MIMEMultipart('alternative')</code>, attaching both rich responsive HTML (with corporate headers, status badges, and deficit metrics) and a clean plain text fallback."
    </div>

    <h2>Module 5: Live Hands-On Interactive Demonstration (36:00 – 48:00)</h2>
    <div class="card-action">🖥️ Action: Switch to Swagger UI at http://localhost:8000/docs with Gmail open in side tab.</div>

    <h3>Step 1: Admin Authentication</h3>
    <p>Execute <code>POST /api/v1/auth/login</code> with <code>admin</code> / <code>Admin@123456</code>. Copy token and authorize Swagger.</p>

    <h3>Step 2: Employee Profile Check</h3>
    <p>Execute <code>GET /api/v1/employees/EMP-007</code>. Show active employee Vishrutha (<code>vishrutha7104@gmail.com</code>).</p>

    <h3>Step 3: THE SHOWSTOPPER — Login at 9:00 AM, Exit at 12:00 PM (&lt; 5 Hours)</h3>
    <ol>
      <li>Clock-in: <code>POST /api/v1/attendance/entry</code> with <code>entry_time='09:00'</code>. Show session recorded as incomplete.</li>
      <li>Clock-out: <code>POST /api/v1/attendance/exit</code> with <code>exit_time='12:00'</code>.</li>
      <li>Highlight JSON output: <code>total_hours: 3.0</code>, policy alert triggered.</li>
      <li><strong>Switch live to Gmail Inbox</strong>: Show the arriving email with corporate branding, 3.0h completed, 5.0h required, and 2.0h deficit badge!</li>
    </ol>

    <h3>Step 4: Self-Service Leave & Dynamic Threshold Scaling</h3>
    <ol>
      <li>Submit leave via <code>POST /api/v1/leave</code> (no admin token required).</li>
      <li>Approve leave via <code>PATCH /api/v1/leave/{id}/approve</code>.</li>
      <li>Explain that approved leave days dynamically lower required weekly days & hours, protecting excused staff.</li>
    </ol>

    <h3>Step 5: On-Demand Weekly Audit & CSV Export</h3>
    <ol>
      <li>Execute <code>POST /api/v1/admin/monitoring/run</code> with <code>include_current_week: true</code>.</li>
      <li>Download spreadsheet via <code>GET /api/v1/reports/attendance/export.csv</code>.</li>
    </ol>

    <h2>Module 6: Testing, Code Quality & Reliability (48:00 – 54:00)</h2>
    <div class="card-speech">
      <div class="card-speech-title">🗣️ Speaker Script:</div>
      "Enterprise systems require verified reliability.<br><br>
      • <strong>Automated Test Suite (pytest -v)</strong>: 39 automated asynchronous tests running in ~1.2s with 100% pass rate.<br>
      • <strong>Static Code Analysis (ruff check app tests)</strong>: 0 errors across the entire codebase.<br>
      • <strong>Idempotent Deduplication</strong>: Every email notification generates a unique deduplication key in <code>notification_logs</code>, guaranteeing no duplicate emails."
    </div>

    <h2>Module 7: Q&A, Scalability & Production Roadmap (54:00 – 60:00)</h2>
    <div class="card-speech">
      <div class="card-speech-title">🗣️ Speaker Script:</div>
      "To wrap up before open Q&A, here is how CAMS scales in an enterprise:<br>
      • Physical IoT Turnstile Integration via dedicated machine API keys.<br>
      • Horizontal Scaling behind NGINX / AWS ALB with Redis + Celery worker pools.<br>
      • MongoDB Sharding on <code>(employee_id, date)</code> partition keys.<br><br>
      Thank you! I am now delighted to take your questions."
    </div>

    <h2>Master Q&A Cheatsheet</h2>
    <table>
      <thead>
        <tr><th>Question</th><th>Winning Senior Technical Answer</th></tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>Why PyMongo Async over Motor?</strong></td>
          <td>Motor wraps sync drivers in threadpools and has deprecation issues in modern Python. PyMongo Async (<code>AsyncMongoClient</code>) provides native event loop integration and sub-millisecond query execution without ORM overhead.</td>
        </tr>
        <tr>
          <td><strong>How are multiple punches handled?</strong></td>
          <td>CAMS sums all completed sessions on that date. As long as cumulative active hours reach 5.0 hours, the employee is fully compliant.</td>
        </tr>
        <tr>
          <td><strong>What if an employee forgets to clock out?</strong></td>
          <td>Open sessions remain incomplete. HR administrators can regularize the session via <code>PATCH /attendance/session/{id}</code>, with all changes recorded in <code>audit_logs</code>.</td>
        </tr>
        <tr>
          <td><strong>How does the leave system prevent fraud?</strong></td>
          <td><code>leave_repo</code> executes an overlap query checking date ranges against existing requests. Any collision immediately returns 409 Conflict.</td>
        </tr>
      </tbody>
    </table>

  </div>
</div>
</body>
</html>"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Generated 1-Hour HTML Document: {out_path}")

if __name__ == "__main__":
    build_1_hour_docx(os.path.abspath("DEMO_SCRIPT_1_HOUR.docx"))
    build_1_hour_html(os.path.abspath("DEMO_SCRIPT_1_HOUR.html"))
