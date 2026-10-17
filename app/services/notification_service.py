"""Email/SMTP notification service with professional HTML and plain text templates."""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


class NotificationService:
    """
    Sends attendance violation emails with professional HTML & plain-text templates.

    Delivery modes:
      - smtp    : real SMTP delivery (HTML + plaintext multipart)
      - console : log to stdout (development)
      - disabled: no delivery
    """

    async def send_violation_email(
        self,
        employee_email: str,
        employee_name: str,
        week_start: str,
        week_end: str,
        violations: list[str],
        employee_id: str | None = None,
        department: str | None = None,
    ) -> bool:
        """Send a weekly policy violation notification email."""
        settings = get_settings()
        mode = settings.email_delivery_mode

        emp_code = f" [{employee_id}]" if employee_id else ""
        subject = f"Weekly Attendance Policy Notice — Week of {week_start}{emp_code}"
        body = _build_violation_email_body(
            employee_name=employee_name,
            employee_id=employee_id or "N/A",
            department=department or "General",
            employee_email=employee_email,
            week_start=week_start,
            week_end=week_end,
            violations=violations,
        )
        html_body = _build_weekly_violation_html(
            employee_name=employee_name,
            employee_id=employee_id or "N/A",
            department=department or "General",
            employee_email=employee_email,
            week_start=week_start,
            week_end=week_end,
            violations=violations,
        )

        if mode == "disabled":
            logger.info("Email delivery disabled. Skipping notification for %s.", employee_email)
            return True

        if mode == "console":
            logger.info(
                "=== [CONSOLE EMAIL] To: %s | Subject: %s ===\n%s\n=== END EMAIL ===",
                employee_email,
                subject,
                body,
            )
            return True

        return await _send_via_smtp(employee_email, subject, body, settings, html_body=html_body)

    async def send_daily_violation_email(
        self,
        employee_email: str,
        employee_name: str,
        employee_id: str,
        attendance_date: str,
        hours_worked: float,
        min_required_hours: float = 5.0,
        department: str | None = None,
        entry_time_str: str | None = None,
        exit_time_str: str | None = None,
    ) -> bool:
        """Send an automatic daily violation email when an employee works less than 5 hours."""
        settings = get_settings()
        mode = settings.email_delivery_mode

        deficit = max(0.0, round(min_required_hours - hours_worked, 2))
        subject = (
            f"Attendance Policy Alert: Under {min_required_hours:.0f} Hours on "
            f"{attendance_date} [{employee_id} - {employee_name}]"
        )
        body = _build_daily_violation_email_body(
            employee_name=employee_name,
            employee_id=employee_id,
            department=department or "General",
            employee_email=employee_email,
            attendance_date=attendance_date,
            hours_worked=hours_worked,
            min_required_hours=min_required_hours,
            deficit=deficit,
            entry_time_str=entry_time_str,
            exit_time_str=exit_time_str,
        )
        html_body = _build_daily_violation_html(
            employee_name=employee_name,
            employee_id=employee_id,
            department=department or "General",
            employee_email=employee_email,
            attendance_date=attendance_date,
            hours_worked=hours_worked,
            min_required_hours=min_required_hours,
            deficit=deficit,
            entry_time_str=entry_time_str,
            exit_time_str=exit_time_str,
        )

        if mode == "disabled":
            logger.info("Email delivery disabled. Skipping daily alert for %s.", employee_email)
            return True

        if mode == "console":
            logger.info(
                "=== [CONSOLE EMAIL] To: %s | Subject: %s ===\n%s\n=== END EMAIL ===",
                employee_email,
                subject,
                body,
            )
            return True

        return await _send_via_smtp(employee_email, subject, body, settings, html_body=html_body)

    async def send_password_reset_email(
        self,
        to_email: str,
        user_name: str,
        reset_code: str,
        tenant_id: str,
    ) -> bool:
        """Send a password reset verification code email."""
        settings = get_settings()
        mode = settings.email_delivery_mode
        subject = f"Password Reset Code: {reset_code} — CAMS ({tenant_id})"
        body = (
            f"Hello {user_name},\n\n"
            f"You requested to reset your password for organization '{tenant_id}'.\n\n"
            f"Your verification code is: {reset_code}\n\n"
            f"This code will expire in 15 minutes.\n\n"
            f"If you did not request this, please ignore this email.\n\n"
            f"— CAMS Security Team\n"
        )
        html_body = (
            "<div style='font-family:sans-serif; max-width:500px; margin:auto; "
            "padding:20px; border:1px solid #e2e8f0; border-radius:8px;'>"
            "<h2 style='color:#4f46e5; margin-bottom:10px;'>Password Reset</h2>"
            f"<p>Hello <strong>{user_name}</strong>,</p>"
            f"<p>We received a password reset request for <code>{tenant_id}</code>.</p>"
            "<div style='background:#f1f5f9; padding:15px; border-radius:6px; "
            "text-align:center; margin:20px 0;'>"
            f"<span style='font-size:24px; font-weight:700; letter-spacing:4px; "
            f"color:#1e293b;'>{reset_code}</span>"
            "</div>"
            "<p style='color:#64748b; font-size:13px;'>"
            "This code expires in 15 minutes. Enter this code to set your new password.</p>"
            "<hr style='border:none; border-top:1px solid #e2e8f0; margin:20px 0;'>"
            "<p style='color:#94a3b8; font-size:11px;'>"
            "If you did not request this, you can safely ignore this email.</p>"
            "</div>"
        )

        if mode == "disabled":
            logger.info("Email delivery disabled. Reset code for %s: %s", to_email, reset_code)
            return True

        if mode == "console":
            logger.info(
                "=== [CONSOLE EMAIL] To: %s | Subject: %s ===\n%s\n=== END EMAIL ===",
                to_email,
                subject,
                body,
            )
            return True

        return await _send_via_smtp(to_email, subject, body, settings, html_body=html_body)


async def _send_via_smtp(
    to_address: str,
    subject: str,
    body: str,
    settings: Any,
    html_body: str | None = None,
) -> bool:
    """Attempt SMTP delivery with multipart/alternative for plain text and rich HTML."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_address}>"
        msg["To"] = to_address
        msg.attach(MIMEText(body, "plain"))
        if html_body:
            msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(
            settings.smtp_host,
            settings.smtp_port,
            timeout=settings.smtp_timeout_seconds,
        ) as server:
            if settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(settings.smtp_from_address, to_address, msg.as_string())

        logger.info("Email sent to %s", to_address)
        return True

    except smtplib.SMTPRecipientsRefused as exc:
        logger.error("SMTP rejected recipient %s: %s", to_address, exc)
        return False
    except smtplib.SMTPAuthenticationError as exc:
        logger.error("SMTP authentication failed: %s", exc)
        return False
    except (smtplib.SMTPException, OSError, TimeoutError) as exc:
        logger.warning("SMTP temporary failure for %s: %s", to_address, exc)
        return False


def _build_daily_violation_email_body(
    employee_name: str,
    employee_id: str,
    department: str,
    employee_email: str,
    attendance_date: str,
    hours_worked: float,
    min_required_hours: float,
    deficit: float,
    entry_time_str: str | None = None,
    exit_time_str: str | None = None,
) -> str:
    return f"""================================================================================
          CENTRAL ATTENDANCE MANAGEMENT SYSTEM — OFFICIAL NOTICE
================================================================================

ATTENTION: DAILY ATTENDANCE POLICY COMPLIANCE ALERT

EMPLOYEE INFORMATION:
--------------------------------------------------------------------------------
  Employee Name:   {employee_name}
  Employee ID:     {employee_id}
  Department:      {department}
  Official Email:  {employee_email}
  Date of Notice:  {attendance_date}

ATTENDANCE SESSION SUMMARY:
--------------------------------------------------------------------------------
  Attendance Date:          {attendance_date}
  Recorded Entry Time:      {entry_time_str or "N/A"}
  Recorded Exit Time:       {exit_time_str or "N/A"}
  Total Working Hours:      {hours_worked:.2f} Hours
  Mandatory Daily Minimum:  {min_required_hours:.1f} Hours
  Hours Deficit:            {deficit:.2f} Hours below required minimum

POLICY REQUIREMENTS:
--------------------------------------------------------------------------------
In accordance with company attendance regulations:
  1. Mandatory Daily Hours:   Every employee must complete at least 5.0 hours
                             per office attendance day.
  2. Mandatory Weekly Days:   Every employee must attend office for at least
                             3 days per week.
  3. Mandatory Weekly Hours:  Total weekly attendance must be at least 15.0 hours.

NON-COMPLIANCE NOTICE:
--------------------------------------------------------------------------------
Because your office attendance for this session was {hours_worked:.2f} hours, it does NOT
fulfill the daily minimum 5-hour requirement and is recorded as non-compliant.

ACTION REQUIRED:
--------------------------------------------------------------------------------
• If you departed early with prior manager approval, please notify HR.
• If this was due to a missed swipe, biometric malfunction, or official emergency,
  please submit an Attendance Correction request in the CAMS portal immediately.
• For questions or exceptions, contact HR Compliance.

================================================================================
This is an automated notification sent by CAMS HR Compliance System.
Do not reply directly to this email.
================================================================================
"""


def _build_daily_violation_html(
    employee_name: str,
    employee_id: str,
    department: str,
    employee_email: str,
    attendance_date: str,
    hours_worked: float,
    min_required_hours: float,
    deficit: float,
    entry_time_str: str | None = None,
    exit_time_str: str | None = None,
) -> str:
    template_path = TEMPLATES_DIR / "daily_violation.html"
    try:
        content = template_path.read_text(encoding="utf-8")
        return content.format(
            employee_name=employee_name,
            employee_id=employee_id,
            department=department,
            employee_email=employee_email,
            attendance_date=attendance_date,
            hours_worked=f"{hours_worked:.2f}",
            min_required_hours=f"{min_required_hours:.1f}",
            deficit=f"{deficit:.2f}",
            entry_time_str=entry_time_str or "N/A",
            exit_time_str=exit_time_str or "N/A",
        )
    except Exception as e:
        logger.warning("Failed to render daily violation HTML template: %s", e)
        return ""


def _build_violation_email_body(
    employee_name: str,
    employee_id: str,
    department: str,
    employee_email: str,
    week_start: str,
    week_end: str,
    violations: list[str],
) -> str:
    violation_list = "\n".join(f"  • {v}" for v in violations)
    return f"""================================================================================
          CENTRAL ATTENDANCE MANAGEMENT SYSTEM — OFFICIAL NOTICE
================================================================================

ATTENTION: WEEKLY ATTENDANCE POLICY NON-COMPLIANCE NOTICE

EMPLOYEE INFORMATION:
--------------------------------------------------------------------------------
  Employee Name:       {employee_name}
  Employee ID:         {employee_id}
  Department:          {department}
  Official Email:      {employee_email}
  Evaluation Period:   {week_start} to {week_end}

POLICY VIOLATIONS DETECTED:
--------------------------------------------------------------------------------
{violation_list}

MANDATORY ATTENDANCE REQUIREMENTS:
--------------------------------------------------------------------------------
  • At least 3 qualifying office attendance days per week
  • At least 15 total office working hours per week
  • An average of at least 5 office hours per attended day

ACTION REQUIRED:
--------------------------------------------------------------------------------
If you believe this notification is in error (e.g. approved leave or system
recording discrepancy), please submit an Attendance Correction request or
contact your HR administrator.

================================================================================
This is an automated message. Do not reply to this email.
CAMS Automated Monitoring System — HR Compliance
================================================================================
"""


def _build_weekly_violation_html(
    employee_name: str,
    employee_id: str,
    department: str,
    employee_email: str,
    week_start: str,
    week_end: str,
    violations: list[str],
) -> str:
    template_path = TEMPLATES_DIR / "weekly_violation.html"
    try:
        content = template_path.read_text(encoding="utf-8")
        violation_items = "".join(
            f'<li style="margin-bottom:6px;"><strong>{v}</strong></li>' for v in violations
        )
        return content.format(
            employee_name=employee_name,
            employee_id=employee_id,
            department=department,
            employee_email=employee_email,
            week_start=week_start,
            week_end=week_end,
            violation_items=violation_items,
        )
    except Exception as e:
        logger.warning("Failed to render weekly violation HTML template: %s", e)
        return ""
