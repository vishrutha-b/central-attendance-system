"""
Idempotent database seeder for CAMS.

Populates:
- Employees across multiple departments
- Company holidays
- Leave requests
- Varied attendance patterns:
  - Compliant employees (>= 3 days, >= 15 hrs, >= 5 avg hrs)
  - Non-compliant employees (< 3 days or < 15 hrs)
  - Split / multi-session days
  - Incomplete sessions (open without exit)
  - Attendance during leave days
"""

from __future__ import annotations

import asyncio
import logging
import sys
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings
from app.database.connection import close_database_connection, connect_to_database, get_database
from app.database.indexes import create_indexes
from app.security.password import hash_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("seed_data")

TZ_KOLKATA = ZoneInfo("Asia/Kolkata")


async def seed() -> None:
    settings = get_settings()
    await connect_to_database()
    db = get_database()
    await create_indexes(db)

    logger.info("Seeding initial administrator...")
    admin_doc = {
        "admin_id": "ADM-000001",
        "username": settings.initial_admin_username,
        "email": settings.initial_admin_email,
        "hashed_password": hash_password(settings.initial_admin_password),
        "role": "admin",
        "is_active": True,
        "created_at": datetime.now(UTC),
    }
    await db.admin_users.update_one(
        {"username": admin_doc["username"]},
        {"$set": admin_doc},
        upsert=True,
    )

    logger.info("Seeding employees...")
    employees = [
        {
            "employee_id": "EMP-001",
            "name": "Aarav Sharma",
            "email": "aarav.sharma@company.com",
            "department": "Engineering",
            "designation": "Senior Backend Engineer",
            "joining_date": "2023-01-15",
            "is_active": True,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        },
        {
            "employee_id": "EMP-002",
            "name": "Diya Patel",
            "email": "diya.patel@company.com",
            "department": "Engineering",
            "designation": "Frontend Developer",
            "joining_date": "2023-03-01",
            "is_active": True,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        },
        {
            "employee_id": "EMP-003",
            "name": "Rohan Verma",
            "email": "rohan.verma@company.com",
            "department": "Sales",
            "designation": "Account Executive",
            "joining_date": "2023-06-10",
            "is_active": True,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        },
        {
            "employee_id": "EMP-004",
            "name": "Priya Nair",
            "email": "priya.nair@company.com",
            "department": "Human Resources",
            "designation": "HR Specialist",
            "joining_date": "2022-11-01",
            "is_active": True,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        },
        {
            "employee_id": "EMP-005",
            "name": "Vikram Singh",
            "email": "vikram.singh@company.com",
            "department": "Operations",
            "designation": "Operations Lead",
            "joining_date": "2023-08-20",
            "is_active": True,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        },
        {
            "employee_id": "EMP-006",
            "name": "Ananya Roy",
            "email": "ananya.roy@company.com",
            "department": "Finance",
            "designation": "Financial Analyst",
            "joining_date": "2024-01-05",
            "is_active": False,  # Inactive employee example
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        },
    ]

    for emp in employees:
        await db.employees.update_one(
            {"employee_id": emp["employee_id"]},
            {"$set": emp},
            upsert=True,
        )

    logger.info("Seeding company holidays...")
    current_year = date.today().year
    holidays = [
        {
            "holiday_id": f"HOL-{current_year}-01",
            "name": "New Year's Day",
            "date": f"{current_year}-01-01",
            "description": "National holiday",
        },
        {
            "holiday_id": f"HOL-{current_year}-02",
            "name": "Republic Day",
            "date": f"{current_year}-01-26",
            "description": "National holiday",
        },
        {
            "holiday_id": f"HOL-{current_year}-03",
            "name": "Independence Day",
            "date": f"{current_year}-08-15",
            "description": "National holiday",
        },
        {
            "holiday_id": f"HOL-{current_year}-04",
            "name": "Gandhi Jayanti",
            "date": f"{current_year}-10-02",
            "description": "National holiday",
        },
        {
            "holiday_id": f"HOL-{current_year}-05",
            "name": "Christmas",
            "date": f"{current_year}-12-25",
            "description": "Festival",
        },
    ]
    for hol in holidays:
        await db.holidays.update_one(
            {"holiday_id": hol["holiday_id"]},
            {"$set": hol},
            upsert=True,
        )

    logger.info("Seeding leave requests...")
    # Seed sample leaves for EMP-004 and EMP-005
    today = date.today()
    last_week_start = today - timedelta(days=today.weekday() + 7)  # Previous Monday
    leaves = [
        {
            "leave_id": "LV-001",
            "employee_id": "EMP-004",
            "start_date": (
                last_week_start + timedelta(days=3)
            ).isoformat(),  # Thursday of last week
            "end_date": (last_week_start + timedelta(days=4)).isoformat(),  # Friday of last week
            "reason": "Family function",
            "status": "approved",
            "reviewed_by": "ADM-000001",
            "reviewed_at": datetime.now(UTC),
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        },
        {
            "leave_id": "LV-002",
            "employee_id": "EMP-005",
            "start_date": (today + timedelta(days=7)).isoformat(),
            "end_date": (today + timedelta(days=8)).isoformat(),
            "reason": "Personal time off",
            "status": "pending",
            "reviewed_by": None,
            "reviewed_at": None,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        },
    ]
    for lv in leaves:
        await db.leave_requests.update_one(
            {"leave_id": lv["leave_id"]},
            {"$set": lv},
            upsert=True,
        )

    logger.info("Seeding attendance sessions...")
    # Generate past completed week sessions
    # Monday to Friday for last week:
    # EMP-001: 5 full days (8 hrs/day) -> Fully compliant
    # EMP-002: 3 days (6 hrs/day = 18 hrs) -> Compliant
    # EMP-003: 2 days (4 hrs/day = 8 hrs) -> Non-compliant (< 3 days, < 15 hrs)
    # EMP-004: Multi-sessions on Mon, Tue, Wed (2x4h) + approved leave Thu/Fri
    #          -> Compliant with leave adjustment
    # EMP-005: 1 incomplete session on Wednesday
    sessions = []

    # EMP-001: Mon to Fri, 09:00 to 17:30 (8.5 hrs each day)
    for d in range(5):
        s_date = last_week_start + timedelta(days=d)
        entry_dt = datetime.combine(s_date, time(9, 0), tzinfo=TZ_KOLKATA).astimezone(UTC)
        exit_dt = datetime.combine(s_date, time(17, 30), tzinfo=TZ_KOLKATA).astimezone(UTC)
        total_hours = 8.5
        sessions.append(
            {
                "attendance_id": f"ATT-SEED-001-{d}",
                "employee_id": "EMP-001",
                "date": s_date.isoformat(),
                "entry_time": entry_dt,
                "exit_time": exit_dt,
                "total_hours": total_hours,
                "attendance_status": "present",
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            }
        )

    # EMP-002: Mon, Tue, Wed (09:30 to 15:30 -> 6.0 hrs each = 18 hrs total)
    for d in range(3):
        s_date = last_week_start + timedelta(days=d)
        entry_dt = datetime.combine(s_date, time(9, 30), tzinfo=TZ_KOLKATA).astimezone(UTC)
        exit_dt = datetime.combine(s_date, time(15, 30), tzinfo=TZ_KOLKATA).astimezone(UTC)
        sessions.append(
            {
                "attendance_id": f"ATT-SEED-002-{d}",
                "employee_id": "EMP-002",
                "date": s_date.isoformat(),
                "entry_time": entry_dt,
                "exit_time": exit_dt,
                "total_hours": 6.0,
                "attendance_status": "present",
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            }
        )

    # EMP-003: Mon, Tue only (10:00 to 14:00 -> 4.0 hrs each = 8 hrs total) -> Non-compliant
    for d in range(2):
        s_date = last_week_start + timedelta(days=d)
        entry_dt = datetime.combine(s_date, time(10, 0), tzinfo=TZ_KOLKATA).astimezone(UTC)
        exit_dt = datetime.combine(s_date, time(14, 0), tzinfo=TZ_KOLKATA).astimezone(UTC)
        sessions.append(
            {
                "attendance_id": f"ATT-SEED-003-{d}",
                "employee_id": "EMP-003",
                "date": s_date.isoformat(),
                "entry_time": entry_dt,
                "exit_time": exit_dt,
                "total_hours": 4.0,
                "attendance_status": "present",
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            }
        )

    # EMP-004: Mon, Tue, Wed multi-sessions (09:00 - 13:00 and 14:00 - 18:00)
    for d in range(3):
        s_date = last_week_start + timedelta(days=d)
        # Session 1
        e1 = datetime.combine(s_date, time(9, 0), tzinfo=TZ_KOLKATA).astimezone(UTC)
        x1 = datetime.combine(s_date, time(13, 0), tzinfo=TZ_KOLKATA).astimezone(UTC)
        sessions.append(
            {
                "attendance_id": f"ATT-SEED-004-{d}-1",
                "employee_id": "EMP-004",
                "date": s_date.isoformat(),
                "entry_time": e1,
                "exit_time": x1,
                "total_hours": 4.0,
                "attendance_status": "present",
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            }
        )
        # Session 2
        e2 = datetime.combine(s_date, time(14, 0), tzinfo=TZ_KOLKATA).astimezone(UTC)
        x2 = datetime.combine(s_date, time(18, 0), tzinfo=TZ_KOLKATA).astimezone(UTC)
        sessions.append(
            {
                "attendance_id": f"ATT-SEED-004-{d}-2",
                "employee_id": "EMP-004",
                "date": s_date.isoformat(),
                "entry_time": e2,
                "exit_time": x2,
                "total_hours": 4.0,
                "attendance_status": "present",
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            }
        )

    # EMP-005: 1 complete session on Monday + 1 incomplete session on Tuesday
    m_date = last_week_start
    em = datetime.combine(m_date, time(9, 0), tzinfo=TZ_KOLKATA).astimezone(UTC)
    xm = datetime.combine(m_date, time(17, 0), tzinfo=TZ_KOLKATA).astimezone(UTC)
    sessions.append(
        {
            "attendance_id": "ATT-SEED-005-1",
            "employee_id": "EMP-005",
            "date": m_date.isoformat(),
            "entry_time": em,
            "exit_time": xm,
            "total_hours": 8.0,
            "attendance_status": "present",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
    )
    # Incomplete session
    t_date = last_week_start + timedelta(days=1)
    et = datetime.combine(t_date, time(9, 15), tzinfo=TZ_KOLKATA).astimezone(UTC)
    sessions.append(
        {
            "attendance_id": "ATT-SEED-005-2",
            "employee_id": "EMP-005",
            "date": t_date.isoformat(),
            "entry_time": et,
            "exit_time": None,
            "total_hours": 0.0,
            "attendance_status": "incomplete",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
    )

    for s in sessions:
        await db.attendance.update_one(
            {"attendance_id": s["attendance_id"]},
            {"$set": s},
            upsert=True,
        )

    logger.info("Seeding complete! %d attendance sessions seeded.", len(sessions))
    await close_database_connection()


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
