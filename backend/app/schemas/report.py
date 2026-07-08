from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class TopJobItem(BaseModel):
    job_offer_id: UUID
    title: str
    application_count: int


class RecruitmentSummary(BaseModel):
    total_jobs: int
    active_jobs: int
    total_applications: int
    applications_by_status: dict[str, int]
    acceptance_rate: float          # % accepted over total
    average_score: float | None     # mean total_score across scored candidates
    top_jobs: list[TopJobItem]
    generated_at: datetime


class ReportSnapshotResponse(BaseModel):
    id: UUID
    report_type: str
    title: str | None
    data: dict
    created_at: datetime

    model_config = {"from_attributes": True}
