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

def generate_demo_docx(out_path):
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
    r_s = p_s.add_run("Live Presentation & Technical Demo Script")
    r_s.font.size = Pt(13)
    r_s.font.color.rgb = RGBColor(100, 116, 139)
    
    add_callout(
        doc,
        "Target Audience: Technical Interviewers, Project Evaluators, Clients\n"
        "Estimated Duration: 8 to 12 Minutes\n"
        "Live Swagger URL: http://localhost:8000/docs\n"
        "Live Email Demo: Real Gmail Delivery (Instant 5-Hour Exit Alert)",
        title="PRESENTATION METADATA",
        alert_type="note"
    )
    
    # Pre-demo
    add_header(doc, "Pre-Demo Checklist (Prepare 5 Minutes Before)", level=1)
    checks = [
        "MongoDB is running locally on mongodb://localhost:27017.",
        "FastAPI Server is running in PowerShell: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000",
        "Tab 1 opened: http://localhost:8000/docs (Swagger UI).",
        "Tab 2 opened: Gmail Inbox (vishrutha7104@gmail.com) ready to show the live email landing.",
        "Tab 3 opened: VS Code with project file tree expanded."
    ]
    for c in checks:
        bp = doc.add_paragraph(style='List Bullet')
        bp.paragraph_format.space_after = Pt(2)
        r = bp.add_run(c)
        r.font.size = Pt(9.5)
        
    # Phase 1
    add_header(doc, "Phase 1: Introduction & The Problem Statement (1 - 2 mins)", level=1)
    add_callout(
        doc,
        '"Good morning / afternoon everyone.\n\n'
        'Today, I am presenting the Central Attendance Management System (CAMS) — an enterprise-grade '
        'backend service built with Python 3.12, FastAPI, and asynchronous MongoDB.\n\n'
        'Modern hybrid work environments require transparent, deterministic attendance policies. Many companies '
        'mandate that employees attend the office at least 3 days a week, complete a minimum of 15 hours per week, '
        'and maintain at least a 5-hour daily presence.\n\n'
        'Traditional HR systems only detect attendance shortfalls at the end of the month during payroll processing. '
        'By then, it is too late to correct.\n\n'
        'Our system solves this with instant, real-time enforcement:\n'
        '1. If an employee logs in and exits before completing the mandatory 5.0 hours, our backend detects the deficit '
        'the exact minute they clock out and immediately dispatches an executive alert email to that person.\n'
        '2. At the end of the week, an automated auditor evaluates the 3 days / 15 hours requirement.\n'
        '3. And importantly, our system features a smart leave adjustment engine: approved leaves and company holidays '
        'automatically lower the weekly targets so excused employees never receive wrongful non-compliance notices.\n\n'
        'Let\'s take a quick look at the codebase architecture, and then I will demonstrate the live email delivery."',
        title="SPEAKER SCRIPT — WHAT TO SAY",
        alert_type="speaker"
    )
    
    # Phase 2
    add_header(doc, "Phase 2: Codebase Architecture & File Walkthrough (2 mins)", level=1)
    add_callout(doc, "Switch to VS Code and show the explorer tree.", title="PRESENTER ACTION", alert_type="action")
    add_callout(
        doc,
        '"The project follows a clean 3-tier enterprise architecture:\n\n'
        '• app/main.py: The FastAPI application entrypoint. We use the modern lifespan context manager to manage database '
        'connection pools gracefully and ensure indexes are automatically built on startup.\n'
        '• app/api/v1/: Contains our RESTful routers:\n'
        '   - attendance.py: Endpoints for clock-in (/entry), clock-out (/exit), and single-click combined sessions (/quick-record).\n'
        '   - leave.py: Allows employees to submit leave requests without needing admin credentials, plus admin approvals.\n'
        '   - employees.py: Full employee lifecycle CRUD operations.\n'
        '   - reports.py: Unified attendance compliance reports and downloadable CSV spreadsheets.\n'
        '• app/services/: Houses our core business rules:\n'
        '   - attendance_service.py: Computes session durations and immediately evaluates the 5-hour threshold on exit.\n'
        '   - policy_service.py: The deterministic rules engine auditing the 3-day / 15-hour policy with leave scaling.\n'
        '   - notification_service.py: Dispatches multi-part MIME emails with executive HTML templates and plain text fallbacks.\n'
        '• app/templates/: Houses daily_violation.html and weekly_violation.html for corporate email branding.\n'
        '• app/database/: Built strictly with PyMongo Async (AsyncMongoClient) for non-blocking I/O without heavy ORM overhead.\n'
        '• tests/: Validated with 39 automated tests covering auth, logic, and email dispatch with 100% pass rate."',
        title="SPEAKER SCRIPT — WHAT TO SAY",
        alert_type="speaker"
    )
    
    # Phase 3
    add_header(doc, "Phase 3: How to Explain Gmail SMTP Setup (1 min)", level=1)
    add_callout(doc, "Show the .env file on screen (mask sensitive credentials).", title="PRESENTER ACTION", alert_type="action")
    add_callout(
        doc,
        '"To ensure notifications reach real corporate inboxes reliably, we configured SMTP using Gmail\'s secure relay:\n\n'
        '1. In .env, we set EMAIL_DELIVERY_MODE=smtp, pointing to smtp.gmail.com on port 587 with TLS enabled (SMTP_USE_TLS=true).\n'
        '2. For authentication, Google blocks standard account passwords. Instead, we generate a dedicated 16-digit Google App Password:\n'
        '   • We enable 2-Step Verification on the Google Account.\n'
        '   • Under App Passwords, we create a dedicated 16-character token for CAMS Attendance and set it in .env.\n'
        '   • This allows the application to securely dispatch TLS-encrypted emails without exposing personal account credentials.\n\n'
        'Now, let\'s see the live system in action."',
        title="SPEAKER SCRIPT — WHAT TO SAY",
        alert_type="speaker"
    )
    
    # Phase 4
    add_header(doc, "Phase 4: Live Interactive Swagger & Email Demo (4 mins)", level=1)
    add_callout(doc, "Switch your browser to http://localhost:8000/docs", title="PRESENTER ACTION", alert_type="action")
    
    steps = [
        ("Step 1: Admin Authentication",
         'Go to POST /api/v1/auth/login. Submit {"username": "admin", "password": "Admin@123456"}. Copy the returned access_token and paste it into Swagger\'s green Authorize button.'),
        ("Step 2: Employee Verification",
         'Show POST /api/v1/employees. Demonstrate that EMP-007 is registered with email vishrutha7104@gmail.com and department Engineering.'),
        ("Step 3: THE SHOWSTOPPER — Clock In at 9:00 AM & Exit Under 5 Hours",
         '1. Clock-in: POST /api/v1/attendance/entry with {"employee_id": "EMP-007", "entry_time": "09:00"}.\n'
         '2. Clock-out: POST /api/v1/attendance/exit with {"employee_id": "EMP-007", "exit_time": "12:00"}.\n'
         '3. Show Swagger JSON output: total_hours = 3.0, policy_alert dispatches alert email.\n'
         '4. Switch to Gmail Inbox tab live: Show the arriving email with corporate branding, employee badge, 3.0h completed, 5.0h required, and 2.0h deficit badge!'),
        ("Step 4: Self-Service Leave Request & Policy Protection",
         '1. Open POST /api/v1/leave (explain no admin token is required for employee submission).\n'
         '2. Submit leave for EMP-007 (Oct 12 - Oct 13, sick leave).\n'
         '3. Approve via PATCH /api/v1/leave/{id}/approve.\n'
         '4. Explain that approved leave days automatically scale down the weekly attendance requirements so excused employees are never flagged.'),
        ("Step 5: Run Weekly Compliance Audit On-Demand",
         'Go to POST /api/v1/admin/monitoring/run. Set include_current_week=true. Execute and show the complete audit breakdown.')
    ]
    for s_title, s_desc in steps:
        add_header(doc, s_title, level=2)
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(4)
        r = p.add_run(s_desc)
        r.font.size = Pt(9.5)
        
    # Phase 5
    add_header(doc, "Phase 5: Conclusion & Summary (1 min)", level=1)
    add_callout(
        doc,
        '"To conclude:\n'
        '1. We delivered an enterprise-grade backend that enforces both daily (5 hrs) and weekly (3 days / 15 hrs) policies.\n'
        '2. Alerts are completely automated and real-time — the employee receives an official email the exact minute they clock out short of 5 hours.\n'
        '3. Leaves and holidays are intelligently accounted for to protect compliant employees.\n'
        '4. The entire system is built with modern asynchronous Python, robust error handling, and 39 automated tests.\n\n'
        'Thank you! I am now happy to take any questions."',
        title="SPEAKER SCRIPT — WHAT TO SAY",
        alert_type="speaker"
    )
    
    # Q&A
    add_header(doc, "Q&A Cheatsheet (Common Questions & Answers)", level=1)
    qa_list = [
        ["Likely Question", "Winning Technical Answer"],
        ["Why PyMongo Async instead of Motor?", "Motor has known deprecation warnings on newer Python releases. PyMongo Async (AsyncMongoClient) provides native, zero-overhead asynchronous MongoDB drivers without unnecessary abstractions."],
        ["What if an employee clocks in and out multiple times a day?", "CAMS aggregates all completed sessions for that date. If the combined active time is at least 5.0 hours, they are fully compliant."],
        ["How are duplicate emails prevented during audits?", "We use an idempotent deduplication key in notification_logs formatted as {employee_id}::{week_start}::violation. If already sent, it skips redundant emails."],
        ["Can this connect to biometric turnstiles?", "Yes. Turnstiles can hit POST /api/v1/attendance/entry and /exit directly on badge scan, or batch upload historical logs via /quick-record."]
    ]
    tbl_qa = doc.add_table(rows=len(qa_list), cols=2)
    tbl_qa.alignment = WD_TABLE_ALIGNMENT.CENTER
    qwidths = [Inches(2.5), Inches(4.0)]
    for r_idx, row in enumerate(qa_list):
        for c_idx, val in enumerate(row):
            c = tbl_qa.cell(r_idx, c_idx)
            c.width = qwidths[c_idx]
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
    print(f"Generated Word document: {out_path}")

def generate_demo_html(out_path):
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CAMS — Live Presentation & Demo Script</title>
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
    max-width: 900px;
    margin: 0 auto;
    background: #ffffff;
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.06);
    border: 1px solid var(--border);
    overflow: hidden;
  }
  .header {
    background: var(--primary);
    color: #ffffff;
    padding: 36px 40px;
    border-bottom: 4px solid var(--accent);
  }
  .badge {
    display: inline-block;
    background: rgba(255,255,255,0.15);
    color: #93c5fd;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    padding: 4px 10px;
    border-radius: 4px;
    margin-bottom: 10px;
  }
  .header h1 { font-size: 26px; font-weight: 800; margin-bottom: 6px; }
  .header p { color: #94a3b8; font-size: 14px; }
  .content { padding: 40px; }
  h2 {
    font-size: 20px;
    font-weight: 700;
    color: var(--primary);
    border-bottom: 2px solid var(--border);
    padding-bottom: 8px;
    margin: 36px 0 16px 0;
  }
  h2:first-of-type { margin-top: 0; }
  h3 { font-size: 16px; font-weight: 700; color: var(--primary); margin: 24px 0 10px 0; }
  .card-speech {
    background: var(--success-light);
    border-left: 4px solid var(--success);
    padding: 16px 20px;
    border-radius: 0 8px 8px 0;
    margin: 16px 0;
    font-size: 14.5px;
    font-style: italic;
    color: #14532d;
  }
  .card-speech-title {
    font-style: normal;
    font-weight: 700;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #166534;
    margin-bottom: 8px;
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
  ul, ol { padding-left: 22px; margin-bottom: 16px; }
  li { margin-bottom: 6px; font-size: 14px; }
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
    padding: 10px 14px;
  }
  td {
    padding: 10px 14px;
    border-bottom: 1px solid var(--border);
  }
  tr:nth-child(even) { background: #f8fafc; }
  @media print {
    body { padding: 0; background: #fff; }
    .container { box-shadow: none; border: none; }
  }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="badge">Presentation & Live Demo Guide</div>
    <h1>Central Attendance Management System (CAMS)</h1>
    <p>Live Demo Script, File Walkthrough, SMTP Guide & Presentation Cheatsheet</p>
  </div>
  <div class="content">

    <h2>Pre-Demo Checklist (5 Minutes Before)</h2>
    <ul>
      <li><strong>MongoDB Running</strong>: Verify <code>mongodb://localhost:27017</code> is active.</li>
      <li><strong>FastAPI Running</strong>: <code>uvicorn app.main:app --reload --host 0.0.0.0 --port 8000</code></li>
      <li><strong>Browser Tabs Ready</strong>:
        <ol>
          <li><code>http://localhost:8000/docs</code> (Swagger UI)</li>
          <li>Your Gmail Inbox (<code>vishrutha7104@gmail.com</code>) to show live email landing</li>
          <li>VS Code with project folder expanded</li>
        </ol>
      </li>
    </ul>

    <h2>Phase 1: Introduction & The Problem Statement (1 - 2 mins)</h2>
    <div class="card-speech">
      <div class="card-speech-title">🗣️ What to Say (Word-for-Word):</div>
      "Good morning / afternoon everyone.<br><br>
      Today, I am presenting the <strong>Central Attendance Management System (CAMS)</strong> — an enterprise-grade backend service built with Python 3.12, FastAPI, and asynchronous MongoDB.<br><br>
      In modern hybrid work models, companies mandate that employees attend the office at least <strong>3 days a week</strong>, complete a minimum of <strong>15 hours per week</strong>, and maintain at least a <strong>5-hour daily presence</strong>.<br><br>
      Traditional HR systems only detect attendance shortfalls at the end of the month during payroll processing. By then, it is too late to correct.<br><br>
      Our system solves this with <strong>instant, real-time enforcement</strong>:<br>
      1. If an employee logs in and exits before completing the mandatory 5.0 hours, our backend detects the deficit <strong>the exact minute they clock out</strong> and dispatches an executive alert email to that person immediately.<br>
      2. At the end of the week, an automated auditor evaluates the 3 days / 15 hours requirement.<br>
      3. And importantly, our system includes a <strong>smart leave adjustment engine</strong>: approved leaves and company holidays automatically lower weekly targets so excused employees never receive wrongful violation notices.<br><br>
      Let's take a quick look at the codebase architecture, and then I will demonstrate the live email delivery."
    </div>

    <h2>Phase 2: Codebase Architecture & File Walkthrough (2 mins)</h2>
    <div class="card-action">🖥️ Action: Switch to VS Code and expand the project tree.</div>
    <div class="card-speech">
      <div class="card-speech-title">🗣️ What to Say:</div>
      "The project follows a clean 3-tier enterprise architecture:<br><br>
      • <strong>app/main.py</strong>: The FastAPI application entrypoint using the modern lifespan context manager to manage database connection pools gracefully and ensure indexes are automatically built on startup.<br>
      • <strong>app/api/v1/</strong>: Contains our RESTful routers:<br>
      &nbsp;&nbsp;- <code>attendance.py</code>: Endpoints for clock-in (<code>/entry</code>), clock-out (<code>/exit</code>), and single-click combined sessions (<code>/quick-record</code>).<br>
      &nbsp;&nbsp;- <code>leave.py</code>: Allows employees to submit leave requests without needing admin credentials, plus admin approvals.<br>
      &nbsp;&nbsp;- <code>employees.py</code>: Full employee lifecycle CRUD operations.<br>
      &nbsp;&nbsp;- <code>reports.py</code>: Unified attendance compliance reports and downloadable CSV spreadsheets.<br>
      • <strong>app/services/</strong>: Houses our core business rules:<br>
      &nbsp;&nbsp;- <code>attendance_service.py</code>: Computes session durations and immediately evaluates the 5-hour threshold on exit.<br>
      &nbsp;&nbsp;- <code>policy_service.py</code>: Deterministic rules engine auditing the 3-day / 15-hour policy with leave scaling.<br>
      &nbsp;&nbsp;- <code>notification_service.py</code>: Dispatches multi-part MIME emails with executive HTML templates and plain text fallbacks.<br>
      • <strong>app/templates/</strong>: Houses <code>daily_violation.html</code> and <code>weekly_violation.html</code> for corporate email branding.<br>
      • <strong>app/database/</strong>: Built strictly with PyMongo Async (<code>AsyncMongoClient</code>) for non-blocking I/O without heavy ORMs.<br>
      • <strong>tests/</strong>: Validated with <strong>39 automated tests</strong> covering security, token authentication, and email triggers with 100% pass rate."
    </div>

    <h2>Phase 3: How to Explain Gmail SMTP Setup (1 min)</h2>
    <div class="card-action">🖥️ Action: Show the .env file on screen.</div>
    <div class="card-speech">
      <div class="card-speech-title">🗣️ What to Say:</div>
      "To ensure notifications reach real corporate inboxes reliably, we configured SMTP using Gmail's secure relay:<br><br>
      1. In <code>.env</code>, we set <code>EMAIL_DELIVERY_MODE=smtp</code>, pointing to <code>smtp.gmail.com</code> on port 587 with TLS enabled.<br>
      2. For authentication, Google blocks standard account passwords. Instead, we generate a dedicated 16-digit Google App Password:<br>
      &nbsp;&nbsp;• We enable 2-Step Verification on the Google Account.<br>
      &nbsp;&nbsp;• Under App Passwords, we create a dedicated 16-character token for 'CAMS Attendance' and set it in <code>.env</code>.<br>
      &nbsp;&nbsp;• This allows the backend to safely dispatch TLS-encrypted emails without exposing personal credentials.<br><br>
      Now, let's see the live system in action."
    </div>

    <h2>Phase 4: Live Interactive Swagger & Email Demo (4 mins)</h2>
    <div class="card-action">🖥️ Action: Switch browser to http://localhost:8000/docs</div>

    <h3>Step 1: Admin Authentication</h3>
    <p>Go to <code>POST /api/v1/auth/login</code>. Submit <code>{"username": "admin", "password": "Admin@123456"}</code>. Copy the returned token and authorize Swagger.</p>

    <h3>Step 2: Employee Verification</h3>
    <p>Verify that employee <code>EMP-007</code> (Vishrutha, <code>vishrutha7104@gmail.com</code>) is active in the database.</p>

    <h3>Step 3: THE SHOWSTOPPER — Clock In at 9:00 AM & Exit Under 5 Hours</h3>
    <ol>
      <li>Clock in: <code>POST /api/v1/attendance/entry</code> with <code>{"employee_id": "EMP-007", "entry_time": "09:00"}</code>.</li>
      <li>Clock out: <code>POST /api/v1/attendance/exit</code> with <code>{"employee_id": "EMP-007", "exit_time": "12:00"}</code>.</li>
      <li>Show the JSON response: <code>total_hours: 3.0</code>, policy alert triggers automated email.</li>
      <li><strong>Switch to Gmail Inbox live</strong>: Show the corporate email arriving with Employee Name, ID, 3.0h completed, 5.0h required, and 2.0h deficit badge!</li>
    </ol>

    <h3>Step 4: Self-Service Leave Request & Policy Protection</h3>
    <ol>
      <li>Submit leave: <code>POST /api/v1/leave</code> (no admin token required).</li>
      <li>Approve leave: <code>PATCH /api/v1/leave/{id}/approve</code>.</li>
      <li>Explain that approved leaves automatically reduce weekly targets so excused employees are protected from violation emails.</li>
    </ol>

    <h3>Step 5: Run Weekly Compliance Audit On-Demand</h3>
    <p>Execute <code>POST /api/v1/admin/monitoring/run</code> with <code>include_current_week: true</code> to show full audit compliance stats.</p>

    <h2>Phase 5: Conclusion & Summary (1 min)</h2>
    <div class="card-speech">
      <div class="card-speech-title">🗣️ What to Say:</div>
      "To conclude:<br>
      1. We built an enterprise-grade backend that enforces both daily (5 hrs) and weekly (3 days / 15 hrs) policies.<br>
      2. Alerts are completely automated and real-time — the employee receives an official email the exact minute they clock out short of 5 hours.<br>
      3. Leaves and holidays are intelligently accounted for to protect compliant employees.<br>
      4. The entire system is backed by modern asynchronous Python and 39 automated tests.<br><br>
      Thank you! I am now happy to take any questions."
    </div>

    <h2>Q&A Cheatsheet (Common Questions & Winning Answers)</h2>
    <table>
      <thead>
        <tr><th>Question</th><th>Winning Technical Answer</th></tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>Why PyMongo Async instead of Motor?</strong></td>
          <td>Motor has deprecation warnings on newer Python versions. PyMongo Async (<code>AsyncMongoClient</code>) is the official native asynchronous driver from MongoDB without heavy ORM overhead.</td>
        </tr>
        <tr>
          <td><strong>What if an employee clocks in and out multiple times a day?</strong></td>
          <td>CAMS aggregates all completed sessions for that date. If cumulative active hours reach 5.0 hours, they are fully compliant.</td>
        </tr>
        <tr>
          <td><strong>How are duplicate emails prevented during audits?</strong></td>
          <td>We use an idempotent deduplication key in <code>notification_logs</code> formatted as <code>{employee_id}::{week_start}::violation</code>. If already sent, it skips duplicate emails.</td>
        </tr>
        <tr>
          <td><strong>Can this connect to biometric turnstiles?</strong></td>
          <td>Yes. Turnstiles can hit <code>POST /api/v1/attendance/entry</code> and <code>/exit</code> directly on badge swipe, or batch upload historical logs via <code>/quick-record</code>.</td>
        </tr>
      </tbody>
    </table>

  </div>
</div>
</body>
</html>"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Generated HTML document: {out_path}")

if __name__ == "__main__":
    generate_demo_docx(os.path.abspath("DEMO_SCRIPT.docx"))
    generate_demo_html(os.path.abspath("DEMO_SCRIPT.html"))
