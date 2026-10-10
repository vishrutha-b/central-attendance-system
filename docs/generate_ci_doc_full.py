import os
from pathlib import Path
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

def set_cell_margins(cell, top=100, bottom=100, left=140, right=140):
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

def add_header_styled(doc, text, level):
    p = doc.add_heading(text, level=level)
    run = p.runs[0]
    run.font.name = "Calibri"
    if level == 1:
        run.font.size = Pt(17)
        run.font.color.rgb = RGBColor(15, 23, 42)
        run.font.bold = True
        p.paragraph_format.space_before = Pt(18)
        p.paragraph_format.space_after = Pt(6)
    elif level == 2:
        run.font.size = Pt(13)
        run.font.color.rgb = RGBColor(30, 41, 59)
        run.font.bold = True
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(4)
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
    cell.width = Inches(6.8)
    
    bg_color = "F8FAFC"
    border_color = "3B82F6"
    if alert_type == "warning":
        bg_color = "FFFBEB"
        border_color = "F59E0B"
    elif alert_type == "success":
        bg_color = "F0FDF4"
        border_color = "10B981"
        
    set_cell_background(cell, bg_color)
    set_cell_margins(cell, top=140, bottom=140, left=180, right=140)
    
    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:top w:val="none"/>'
        f'<w:left w:val="single" w:sz="24" w:space="0" w:color="{border_color}"/>'
        f'<w:bottom w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'</w:tcBorders>'
    )
    tcPr.append(borders)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    
    if title:
        r_title = p.add_run(f"{title}: ")
        r_title.bold = True
        r_title.font.name = "Calibri"
        r_title.font.size = Pt(10)
        r_title.font.color.rgb = RGBColor(30, 41, 59)
        
    r_text = p.add_run(text)
    r_text.font.name = "Calibri"
    r_text.font.size = Pt(9.5)
    r_text.font.color.rgb = RGBColor(51, 65, 85)
    
    p_after = doc.add_paragraph()
    p_after.paragraph_format.space_before = Pt(0)
    p_after.paragraph_format.space_after = Pt(4)

def build_full_docx(output_path):
    doc = Document()
    
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)
        
    # Title Block
    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_before = Pt(10)
    title_p.paragraph_format.space_after = Pt(4)
    run_title = title_p.add_run("Central Attendance Management System (CAMS)")
    run_title.font.name = "Calibri"
    run_title.font.size = Pt(24)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(15, 23, 42)
    
    subtitle_p = doc.add_paragraph()
    subtitle_p.paragraph_format.space_before = Pt(0)
    subtitle_p.paragraph_format.space_after = Pt(12)
    run_sub = subtitle_p.add_run("Automated CI/CD Pipeline & DevSecOps Architecture Specification")
    run_sub.font.name = "Calibri"
    run_sub.font.size = Pt(13)
    run_sub.font.color.rgb = RGBColor(100, 116, 139)
    
    add_callout(
        doc,
        "Pipeline Config: .github/workflows/ci.yml  |  Tech Stack: Python 3.12, Ruff, MyPy, Bandit, pip-audit, Safety, Gitleaks, Pytest, SonarQube, Docker, Aqua Trivy  |  Service: MongoDB 7.0 Container  |  Architecture: Directed Acyclic Graph (DAG) Tree",
        title="PIPELINE METADATA",
        alert_type="note"
    )
    
    # 1. Executive Summary
    add_header_styled(doc, "1. Executive Summary & Pipeline Objectives", level=1)
    doc.add_paragraph(
        "The Central Attendance Management System (CAMS) CI/CD pipeline enforces automated quality, security, "
        "and testing verification on every code push and pull request. Designed as a Directed Acyclic Graph (DAG) "
        "tree pipeline, it eliminates manual deployment errors and guarantees enterprise-grade DevSecOps standards."
    )
    
    bullets = [
        ("Fast-Fail Syntax Gate: ", "Compiles the full Python AST before starting heavy database services, catching syntax flaws in under 10 seconds."),
        ("Parallel Quality & Security Verification: ", "Runs code linting (Ruff), static typing (MyPy), SAST security analysis (Bandit), CVE dependency auditing (pip-audit & Safety), and secret leakage protection (Gitleaks) concurrently."),
        ("Isolated Database Testing: ", "Automatically provisions a fresh, healthy MongoDB 7.0 container in CI to execute all 39 Unit and API integration tests with coverage reporting."),
        ("Continuous Code Health & Quality Gate: ", "Aggregates test coverage reports into SonarQube / SonarCloud to monitor cyclomatic complexity and clean code compliance."),
        ("Container Vulnerability Elimination: ", "Builds the production Docker image and runs an Aqua Security Trivy container vulnerability scan before release approval.")
    ]
    for b_title, b_desc in bullets:
        bp = doc.add_paragraph(style='List Bullet')
        bp.paragraph_format.space_before = Pt(1)
        bp.paragraph_format.space_after = Pt(2)
        r1 = bp.add_run(b_title)
        r1.bold = True
        r1.font.color.rgb = RGBColor(30, 41, 59)
        r2 = bp.add_run(b_desc)
        r2.font.color.rgb = RGBColor(71, 85, 105)
        
    # 2. Pipeline DAG Flow Diagram
    add_header_styled(doc, "2. Pipeline Architecture & Directed Acyclic Graph (DAG) Flow", level=1)
    doc.add_paragraph(
        "Rather than executing as a slow single linear script, the pipeline is architected into 6 modular stages "
        "linked by dependencies (needs:). This displays as a clean visual tree in GitHub Actions:"
    )
    
    p_box = doc.add_paragraph()
    p_box.paragraph_format.left_indent = Inches(0.2)
    p_box.paragraph_format.space_before = Pt(4)
    p_box.paragraph_format.space_after = Pt(10)
    r_box = p_box.add_run(
        "┌─────────────────────────────────────────────────────────────────┐\n"
        "│              Stage 1: SYNTAX & BASE VERIFICATION                │\n"
        "│                  (Python 3.12 + compileall)                     │\n"
        "└────────────────────────────────┬────────────────────────────────┘\n"
        "                                 │\n"
        "         ┌───────────────────────┼───────────────────────┐\n"
        "         ▼                       ▼                       ▼\n"
        "┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐\n"
        "│Stage 2: CODE     │    │Stage 3: SECURITY │    │Stage 4: TESTS &  │\n"
        "│         QUALITY  │    │         SCANS    │    │         COVERAGE │\n"
        "│  (Ruff & MyPy)   │    │(Bandit, Audit,   │    │ (Pytest +        │\n"
        "│                  │    │ Safety, Gitleaks)│    │  MongoDB 7.0)    │\n"
        "└────────┬─────────┘    └────────┬─────────┘    └────────┬─────────┘\n"
        "         │                       │                       │\n"
        "         └───────────────────────┼───────────────────────┘\n"
        "                                 ▼\n"
        "┌─────────────────────────────────────────────────────────────────┐\n"
        "│             Stage 5: SONARQUBE ANALYSIS GATE                    │\n"
        "│          (SonarCloud / SonarScanner Quality Gate)               │\n"
        "└────────────────────────────────┬────────────────────────────────┘\n"
        "                                 ▼\n"
        "┌─────────────────────────────────────────────────────────────────┐\n"
        "│          Stage 6: DOCKER BUILD & VULNERABILITY SCAN             │\n"
        "│                 (Docker Buildx + Aqua Trivy)                    │\n"
        "└─────────────────────────────────────────────────────────────────┘"
    )
    r_box.font.name = "Consolas"
    r_box.font.size = Pt(8.5)
    r_box.font.color.rgb = RGBColor(30, 41, 59)
    
    # 3. Detailed Stage Breakdown
    add_header_styled(doc, "3. Deep-Dive Stage Analysis & Verification Matrix", level=1)
    
    stages_data = [
        (
            "Stage 1: Syntax & Base Verification (syntax-and-setup)",
            "Root Gatekeeper",
            "Validates the entire repository using Python's native compileall utility across app/, tests/, and scripts/.",
            "Fast-fails the pipeline immediately if syntax errors, unclosed strings, or invalid indentations are committed.",
            "python -m compileall app/ tests/ scripts/"
        ),
        (
            "Stage 2: Code Quality & Type Checking (code-quality)",
            "Ruff & MyPy",
            "Runs static linting, PEP 8 formatting validation, import sorting (isort), and static type inference.",
            "Eliminates dead code, prevents undefined variables, and verifies Pydantic model contract definitions.",
            "ruff check app/ tests/ scripts/\nmypy --explicit-package-bases --ignore-missing-imports app/"
        ),
        (
            "Stage 3: Multi-Vector Security Scans (security-scans)",
            "Bandit, pip-audit, Safety & Gitleaks",
            "Comprehensive DevSecOps scanning: SAST analysis on code AST, CVE auditing of third-party wheels, and git history secret detection.",
            "Blocks OWASP Top 10 vulnerabilities (SQL/NoSQL injection, insecure hashes) and guarantees zero API keys or passwords are committed.",
            "bandit -r app/ -ll -s B104\npip-audit -r requirements.txt\nsafety check -r requirements.txt\ngitleaks detect"
        ),
        (
            "Stage 4: Automated Testing & Coverage Suite (test-suite)",
            "Pytest, pytest-cov & MongoDB 7.0 Service",
            "Provisions a healthy, isolated MongoDB 7.0 container with health checks, executes 39 Unit and API tests, and generates coverage.xml.",
            "Validates business logic: instant clock-out deficiency alerts, multi-session calculations, leave deductions, and JWT auth.",
            "pytest tests/unit -v --cov=app --cov-report=xml:coverage.xml\npytest tests/api -v"
        ),
        (
            "Stage 5: SonarQube Clean Code Gate (sonarqube)",
            "SonarScanner / SonarCloud",
            "Imports coverage.xml and measures cyclomatic complexity, code duplications, and security hotspots.",
            "Enforces strict Quality Gate standards. Features conditional execution that skips safely when tokens are not yet added.",
            "sonar-scanner (driven by sonar-project.properties)"
        ),
        (
            "Stage 6: Docker Containerization & Image Scan (docker-build-and-scan)",
            "Docker Buildx & Aqua Trivy",
            "Compiles the production Docker image and inspects both Debian base image layers and installed Python packages for vulnerabilities.",
            "Guarantees that the released container artifact contains zero unmitigated CRITICAL or HIGH CVEs before deployment.",
            "docker build -t central-attendance-system:$SHA .\ntrivy image --severity CRITICAL,HIGH central-attendance-system:$SHA"
        )
    ]
    
    for title, tools, desc, objective, cmd in stages_data:
        add_header_styled(doc, title, level=2)
        p = doc.add_paragraph()
        r1 = p.add_run("Tools / Runtimes: ")
        r1.bold = True
        r1.font.size = Pt(9.5)
        r2 = p.add_run(f"{tools}\n")
        r2.font.size = Pt(9.5)
        
        r3 = p.add_run("Primary Objective: ")
        r3.bold = True
        r3.font.size = Pt(9.5)
        r4 = p.add_run(f"{objective}\n")
        r4.font.size = Pt(9.5)
        
        r5 = p.add_run("Description: ")
        r5.bold = True
        r5.font.size = Pt(9.5)
        r6 = p.add_run(f"{desc}")
        r6.font.size = Pt(9.5)
        
        p_c = doc.add_paragraph()
        p_c.paragraph_format.left_indent = Inches(0.2)
        p_c.paragraph_format.space_before = Pt(3)
        p_c.paragraph_format.space_after = Pt(8)
        r_c = p_c.add_run(f"Executed Command:\n{cmd}")
        r_c.font.name = "Consolas"
        r_c.font.size = Pt(8.5)
        r_c.font.color.rgb = RGBColor(30, 41, 59)
        
    # 4. Pipeline Matrix Table
    add_header_styled(doc, "4. Pipeline Stage & Quality Gate Matrix", level=1)
    tbl_matrix = doc.add_table(rows=7, cols=4)
    tbl_matrix.alignment = WD_TABLE_ALIGNMENT.CENTER
    matrix_headers = ["Stage", "Job Identifier", "Primary Tools", "Quality / Security Gate"]
    matrix_rows = [
        ("Stage 1", "syntax-and-setup", "Python 3.12 compileall", "Syntax Gate (Fast-Fail)"),
        ("Stage 2", "code-quality", "Ruff, MyPy", "PEP 8 Style & Static Type Gate"),
        ("Stage 3", "security-scans", "Bandit, pip-audit, Safety, Gitleaks", "SAST, Dependency CVE & Secret Gate"),
        ("Stage 4", "test-suite", "Pytest, MongoDB 7.0, pytest-cov", "Functional & API Integration Gate"),
        ("Stage 5", "sonarqube", "SonarCloud / SonarScanner", "Clean Code Quality Gate"),
        ("Stage 6", "docker-build-and-scan", "Docker Buildx, Aqua Trivy", "Container Vulnerability Security Gate")
    ]
    
    for idx, h in enumerate(matrix_headers):
        c = tbl_matrix.cell(0, idx)
        set_cell_background(c, "0F172A")
        set_cell_margins(c, top=80, bottom=80, left=100, right=100)
        p = c.paragraphs[0]
        r = p.add_run(h)
        r.bold = True
        r.font.size = Pt(9)
        r.font.color.rgb = RGBColor(255, 255, 255)
        
    for r_idx, row in enumerate(matrix_rows):
        for c_idx, val in enumerate(row):
            c = tbl_matrix.cell(r_idx + 1, c_idx)
            set_cell_background(c, "F8FAFC" if (r_idx + 1) % 2 == 1 else "FFFFFF")
            set_cell_margins(c, top=60, bottom=60, left=100, right=100)
            p = c.paragraphs[0]
            r = p.add_run(val)
            r.font.size = Pt(8.5)
            if c_idx == 1:
                r.font.name = "Consolas"
                r.bold = True
                
    doc.add_paragraph().paragraph_format.space_after = Pt(10)
    
    # 5. Local Developer Cheatsheet
    add_header_styled(doc, "5. Local Developer Pre-Push Verification Cheatsheet", level=1)
    add_callout(
        doc,
        "Before pushing code to Git, developers can execute this local 4-step PowerShell sequence to guarantee 100% CI pass rate:\n\n"
        "1. Check Syntax:          python -m compileall app/ tests/ scripts/\n"
        "2. Check Style & Lints:   ruff check app/ tests/ scripts/\n"
        "3. Run SAST Security:     bandit -r app/ -ll -s B104\n"
        "4. Run Test Suites:       pytest tests/unit tests/api -v",
        title="LOCAL DEVELOPER CHEATSHEET",
        alert_type="success"
    )
    
    doc.save(output_path)
    print(f"Generated Word document successfully: {output_path}")

def build_full_html(output_path):
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Central Attendance Management System (CAMS) — CI/CD Pipeline & DevSecOps Specification</title>
<style>
  :root {
    --primary: #0f172a;
    --accent: #2563eb;
    --accent-light: #eff6ff;
    --success: #16a34a;
    --success-light: #f0fdf4;
    --warning: #d97706;
    --warning-light: #fffbeb;
    --border: #e2e8f0;
    --text: #1e293b;
    --text-muted: #64748b;
    --bg-card: #ffffff;
    --bg-page: #f8fafc;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    background-color: var(--bg-page);
    color: var(--text);
    line-height: 1.6;
    padding: 40px 20px;
  }
  .container {
    max-width: 900px;
    margin: 0 auto;
    background: var(--bg-card);
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
  .header-badge {
    display: inline-block;
    background: rgba(255,255,255,0.15);
    color: #93c5fd;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    padding: 4px 10px;
    border-radius: 4px;
    margin-bottom: 12px;
  }
  .header h1 {
    font-size: 26px;
    font-weight: 800;
    margin-bottom: 8px;
    letter-spacing: -0.5px;
  }
  .header p {
    color: #94a3b8;
    font-size: 14px;
    line-height: 1.5;
  }
  .meta-pills {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 16px;
  }
  .pill {
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.15);
    color: #cbd5e1;
    font-size: 12px;
    padding: 3px 10px;
    border-radius: 20px;
  }
  .content {
    padding: 40px;
  }
  h2 {
    font-size: 18px;
    font-weight: 700;
    color: var(--primary);
    border-bottom: 2px solid var(--border);
    padding-bottom: 8px;
    margin-top: 36px;
    margin-bottom: 16px;
  }
  .alert {
    padding: 14px 16px;
    border-radius: 6px;
    margin: 16px 0;
    font-size: 13.5px;
    border-left: 4px solid var(--accent);
    background: var(--accent-light);
  }
  .alert-title {
    font-weight: 700;
    margin-bottom: 2px;
  }
  .alert-warning {
    border-left-color: var(--warning);
    background: var(--warning-light);
  }
  .alert-success {
    border-left-color: var(--success);
    background: var(--success-light);
  }
  .diagram-box {
    background: #0f172a;
    color: #93c5fd;
    padding: 18px 20px;
    border-radius: 8px;
    font-family: Consolas, monospace;
    font-size: 12.5px;
    line-height: 1.45;
    overflow-x: auto;
    margin: 16px 0;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 16px 0;
    font-size: 13.5px;
  }
  th, td {
    padding: 10px 14px;
    border: 1px solid var(--border);
    text-align: left;
    vertical-align: top;
  }
  th {
    background: var(--primary);
    color: #ffffff;
    font-weight: 600;
  }
  tr:nth-child(even) {
    background: #f8fafc;
  }
  .stage-card {
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 18px 20px;
    margin-bottom: 18px;
    background: #ffffff;
  }
  .stage-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
  }
  .stage-title {
    font-size: 16px;
    font-weight: 700;
    color: var(--primary);
  }
  .badge {
    display: inline-block;
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 700;
    background: #e2e8f0;
    color: #334155;
  }
  .badge-blue { background: #dbeafe; color: #1e40af; }
  .badge-green { background: #dcfce7; color: #166534; }
  .badge-purple { background: #f3e8ff; color: #6b21a8; }
  pre {
    background: #1e293b;
    color: #f1f5f9;
    padding: 12px 14px;
    border-radius: 6px;
    font-family: Consolas, monospace;
    font-size: 12px;
    overflow-x: auto;
    margin: 8px 0;
  }
  ul {
    padding-left: 20px;
    margin: 10px 0;
    font-size: 14px;
  }
  li {
    margin-bottom: 6px;
    color: #334155;
  }
  li strong {
    color: var(--primary);
  }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="header-badge">DevSecOps & CI/CD Specification</div>
    <h1>Central Attendance Management System (CAMS)</h1>
    <p>Automated Continuous Integration, Multi-Vector Security Auditing, Testing, and Containerization Architecture</p>
    <div class="meta-pills">
      <span class="pill">Pipeline: .github/workflows/ci.yml</span>
      <span class="pill">Architecture: Directed Acyclic Graph (DAG)</span>
      <span class="pill">Python 3.12</span>
      <span class="pill">MongoDB 7.0 Container</span>
      <span class="pill">SonarQube & Trivy</span>
    </div>
  </div>

  <div class="content">
    <div class="alert">
      <div class="alert-title">DOCUMENT PURPOSE</div>
      This document specifies the automated Continuous Integration and Continuous Deployment (CI/CD) pipeline for CAMS. It details every execution stage, testing framework, security scanner, and container verification gate.
    </div>

    <h2>1. Executive Summary & Pipeline Objectives</h2>
    <ul>
      <li><strong>Fast-Fail Syntax Gate:</strong> Compiles Python AST across all modules in under 10 seconds before spinning up database resources.</li>
      <li><strong>Parallel Quality & Security Verification:</strong> Executes Ruff, MyPy, Bandit, pip-audit, Safety, and Gitleaks concurrently to minimize runtime.</li>
      <li><strong>Isolated Database Testing:</strong> Launches an isolated MongoDB 7.0 service container in GitHub Actions to run 39 Unit and API integration tests.</li>
      <li><strong>SonarQube Clean Code Gate:</strong> Tracks test coverage, code duplications, and security hotspots against defined quality standards.</li>
      <li><strong>Container Vulnerability Gate:</strong> Builds the production Docker image and validates container layers using Aqua Security Trivy.</li>
    </ul>

    <h2>2. Pipeline Directed Acyclic Graph (DAG) Architecture</h2>
    <div class="diagram-box">
┌─────────────────────────────────────────────────────────────────┐
│              Stage 1: SYNTAX & BASE VERIFICATION                │
│                  (Python 3.12 + compileall)                     │
└────────────────────────────────┬────────────────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         ▼                       ▼                       ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│Stage 2: CODE     │    │Stage 3: SECURITY │    │Stage 4: TESTS &  │
│         QUALITY  │    │         SCANS    │    │         COVERAGE │
│  (Ruff & MyPy)   │    │(Bandit, Audit,   │    │ (Pytest +        │
│                  │    │ Safety, Gitleaks)│    │  MongoDB 7.0)    │
└────────┬─────────┘    └────────┬─────────┘    └────────┬─────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│             Stage 5: SONARQUBE ANALYSIS GATE                    │
│          (SonarCloud / SonarScanner Quality Gate)               │
└────────────────────────────────┬────────────────────────────────┘
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│          Stage 6: DOCKER BUILD & VULNERABILITY SCAN             │
│                 (Docker Buildx + Aqua Trivy)                    │
└─────────────────────────────────────────────────────────────────┘</div>

    <h2>3. Deep-Dive Stage Analysis</h2>

    <div class="stage-card">
      <div class="stage-header">
        <span class="stage-title">Stage 1: Syntax & Base Verification (syntax-and-setup)</span>
        <span class="badge badge-blue">compileall</span>
      </div>
      <p><strong>Objective:</strong> Fast-fails the pipeline immediately if syntax errors, unclosed strings, or invalid indentations are committed.</p>
      <pre>python -m compileall app/ tests/ scripts/</pre>
    </div>

    <div class="stage-card">
      <div class="stage-header">
        <span class="stage-title">Stage 2: Code Quality & Type Checking (code-quality)</span>
        <span class="badge badge-green">Ruff & MyPy</span>
      </div>
      <p><strong>Objective:</strong> Enforces PEP 8 standards, organizes imports, removes dead code, and validates static types across FastAPI Pydantic models.</p>
      <pre>ruff check app/ tests/ scripts/
mypy --explicit-package-bases --ignore-missing-imports app/</pre>
    </div>

    <div class="stage-card">
      <div class="stage-header">
        <span class="stage-title">Stage 3: Multi-Vector Security Scans (security-scans)</span>
        <span class="badge badge-purple">Bandit, pip-audit, Safety, Gitleaks</span>
      </div>
      <p><strong>Objective:</strong> Eliminates OWASP Top 10 vulnerabilities (SQL/NoSQL injection, insecure crypto), audits dependency CVEs, and prevents secret leaks.</p>
      <pre>bandit -r app/ -ll -s B104
pip-audit -r requirements.txt
safety check -r requirements.txt</pre>
    </div>

    <div class="stage-card">
      <div class="stage-header">
        <span class="stage-title">Stage 4: Automated Testing & Coverage Suite (test-suite)</span>
        <span class="badge badge-blue">Pytest & MongoDB 7.0</span>
      </div>
      <p><strong>Objective:</strong> Spins up a healthy MongoDB 7.0 container, runs 39 Unit and API tests, and exports coverage.xml and test XML artifacts.</p>
      <pre>pytest tests/unit -v --cov=app --cov-report=xml:coverage.xml
pytest tests/api -v</pre>
    </div>

    <div class="stage-card">
      <div class="stage-header">
        <span class="stage-title">Stage 5: SonarQube Clean Code Gate (sonarqube)</span>
        <span class="badge badge-green">SonarScanner / SonarCloud</span>
      </div>
      <p><strong>Objective:</strong> Ingests coverage.xml to inspect code duplication, complexity, and security hot-spots. Cleanly skips if credentials are not yet configured.</p>
      <pre>sonar-scanner (driven by sonar-project.properties)</pre>
    </div>

    <div class="stage-card">
      <div class="stage-header">
        <span class="stage-title">Stage 6: Docker Container Build & Scan (docker-build-and-scan)</span>
        <span class="badge badge-purple">Buildx & Aqua Trivy</span>
      </div>
      <p><strong>Objective:</strong> Assembles the deployable container image and scans Linux base layers and Python dependencies for CRITICAL/HIGH vulnerabilities.</p>
      <pre>docker build -t central-attendance-system:$SHA .
trivy image --severity CRITICAL,HIGH central-attendance-system:$SHA</pre>
    </div>

    <h2>4. Pipeline Stage & Quality Gate Matrix</h2>
    <table>
      <thead>
        <tr>
          <th>Stage</th>
          <th>Job Identifier</th>
          <th>Primary Tools</th>
          <th>Quality / Security Gate</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>Stage 1</strong></td>
          <td><code>syntax-and-setup</code></td>
          <td>Python 3.12 compileall</td>
          <td>Syntax Gate (Fast-Fail)</td>
        </tr>
        <tr>
          <td><strong>Stage 2</strong></td>
          <td><code>code-quality</code></td>
          <td>Ruff, MyPy</td>
          <td>PEP 8 Style & Static Type Gate</td>
        </tr>
        <tr>
          <td><strong>Stage 3</strong></td>
          <td><code>security-scans</code></td>
          <td>Bandit, pip-audit, Safety, Gitleaks</td>
          <td>SAST, Dependency CVE & Secret Gate</td>
        </tr>
        <tr>
          <td><strong>Stage 4</strong></td>
          <td><code>test-suite</code></td>
          <td>Pytest, MongoDB 7.0, pytest-cov</td>
          <td>Functional & API Integration Gate</td>
        </tr>
        <tr>
          <td><strong>Stage 5</strong></td>
          <td><code>sonarqube</code></td>
          <td>SonarCloud / SonarScanner</td>
          <td>Clean Code Quality Gate</td>
        </tr>
        <tr>
          <td><strong>Stage 6</strong></td>
          <td><code>docker-build-and-scan</code></td>
          <td>Docker Buildx, Aqua Trivy</td>
          <td>Container Vulnerability Security Gate</td>
        </tr>
      </tbody>
    </table>

    <h2>5. Local Developer Pre-Push Verification Cheatsheet</h2>
    <div class="alert alert-success">
      <div class="alert-title">QUICK VERIFICATION</div>
      Run this 4-step PowerShell sequence locally before pushing code to Git:
    </div>
    <pre># 1. Check Syntax
python -m compileall app/ tests/ scripts/

# 2. Check Style & Linter
ruff check app/ tests/ scripts/

# 3. Run SAST Security Scan
bandit -r app/ -ll -s B104

# 4. Run Test Suites
pytest tests/unit tests/api -v</pre>
  </div>
</div>
</body>
</html>"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Generated HTML document successfully: {output_path}")

if __name__ == "__main__":
    docx_file = Path("Central_Attendance_System_CI_CD_Pipeline_Documentation.docx").resolve()
    html_file = Path("Central_Attendance_System_CI_CD_Pipeline_Documentation.html").resolve()
    build_full_docx(str(docx_file))
    build_full_html(str(html_file))
