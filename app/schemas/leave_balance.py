"""Leave balance and quota schemas."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field, model_validator

from app.schemas.common import CAMSBaseModel


class LeaveBalanceItem(CAMSBaseModel):
    leave_type: str
    allocated_days: float
    used_days: float
    remaining_days: float


class LeaveBalanceResponse(CAMSBaseModel):
    employee_id: str
    year: int
    balances: list[LeaveBalanceItem]


class LeaveAllocationRequest(CAMSBaseModel):
    employee_id: Annotated[str, Field(min_length=1, max_length=50)]
    year: Annotated[int, Field(ge=2020, le=2050)]
    leave_type: Annotated[str, Field(min_length=2, max_length=50)]
    allocated_days: Annotated[float, Field(ge=0.0, le=365.0)]

    @model_validator(mode="after")
    def normalize_fields(self) -> LeaveAllocationRequest:
        self.employee_id = self.employee_id.strip().upper()
        self.leave_type = self.leave_type.strip().lower()
        return self
