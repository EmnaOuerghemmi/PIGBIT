from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


CAREER_STATUSES = (
    "PROBATION",
    "IN_PROGRESS",
    "PROMOTION_PLANNED",
    "COMPLETED",
    "RETIREMENT_PLANNED",
)


class CareerPlanCreate(BaseModel):
    user_id: UUID
    current_position: str | None = None
    target_position: str | None = None
    status: str = Field(default="IN_PROGRESS", pattern="^(PROBATION|IN_PROGRESS|PROMOTION_PLANNED|COMPLETED|RETIREMENT_PLANNED)$")
    progress: float = Field(default=0.0, ge=0, le=100)
    skills_to_develop: str | None = None
    notes: str | None = None
    target_date: datetime | None = None


class CareerPlanUpdate(BaseModel):
    current_position: str | None = None
    target_position: str | None = None
    status: str | None = Field(default=None, pattern="^(PROBATION|IN_PROGRESS|PROMOTION_PLANNED|COMPLETED|RETIREMENT_PLANNED)$")
    progress: float | None = Field(default=None, ge=0, le=100)
    skills_to_develop: str | None = None
    notes: str | None = None
    target_date: datetime | None = None


class CareerPlanResponse(BaseModel):
    id: UUID
    user_id: UUID
    current_position: str | None
    target_position: str | None
    status: str
    progress: float
    skills_to_develop: str | None
    notes: str | None
    target_date: datetime | None
    created_at: datetime
    updated_at: datetime | None = None
    employee_name: str | None = None

    model_config = {"from_attributes": True}


class CareerStats(BaseModel):
    probation: int
    promotions_planned: int
    in_progress: int
    retirements_planned: int
    total: int
