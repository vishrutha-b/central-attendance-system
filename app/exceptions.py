"""Custom application exceptions with HTTP status mappings."""

from __future__ import annotations

from fastapi import HTTPException, status


class CAMSError(Exception):
    """Base application error."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail: str = "An unexpected error occurred."

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.__class__.detail
        super().__init__(self.detail)

    def to_http(self) -> HTTPException:
        return HTTPException(status_code=self.status_code, detail=self.detail)


class NotFoundError(CAMSError):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Resource not found."


class ConflictError(CAMSError):
    status_code = status.HTTP_409_CONFLICT
    detail = "Resource already exists."


class ValidationError(CAMSError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    detail = "Validation failed."


class BadRequestError(CAMSError):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Bad request."


class UnauthorizedError(CAMSError):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Authentication required."


class ForbiddenError(CAMSError):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "Insufficient permissions."


class DatabaseError(CAMSError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    detail = "Database operation failed."


class ServiceUnavailableError(CAMSError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    detail = "Service temporarily unavailable."


class EmployeeNotFoundError(NotFoundError):
    detail = "Employee not found."


class EmployeeInactiveError(BadRequestError):
    detail = "Employee account is inactive."


class AttendanceNotFoundError(NotFoundError):
    detail = "Attendance record not found."


class AttendanceConflictError(ConflictError):
    detail = "Attendance session conflict."


class AttendanceSequenceError(BadRequestError):
    detail = "Invalid attendance sequence."


class LeaveNotFoundError(NotFoundError):
    detail = "Leave request not found."


class LeaveConflictError(ConflictError):
    detail = "Overlapping leave request exists."


class LeaveTransitionError(BadRequestError):
    detail = "Invalid leave status transition."


class HolidayConflictError(ConflictError):
    detail = "Holiday already exists for this date."


class AdminNotFoundError(NotFoundError):
    detail = "Administrator not found."


class InvalidCredentialsError(UnauthorizedError):
    detail = "Invalid username or password."


class TokenExpiredError(UnauthorizedError):
    detail = "Token has expired."


class InvalidTokenError(UnauthorizedError):
    detail = "Invalid or malformed token."
