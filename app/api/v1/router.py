"""V1 API router — assembles all sub-routers."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.attendance import router as attendance_router
from app.api.v1.auth import router as auth_router
from app.api.v1.employees import router as employees_router
from app.api.v1.leave import holiday_router, leave_router
from app.api.v1.reports import router as reports_router

router = APIRouter(prefix="/api/v1")

router.include_router(auth_router)
router.include_router(employees_router)
router.include_router(attendance_router)
router.include_router(reports_router)
router.include_router(leave_router)
router.include_router(holiday_router)
router.include_router(admin_router)
