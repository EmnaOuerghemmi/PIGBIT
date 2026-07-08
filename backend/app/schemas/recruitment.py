from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class JobOfferCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=10)
    salary_min: float | None = None
    salary_max: float | None = None
    required_skills: list[str] | None = None
    required_experience_years: float | None = None
    required_education_level: str | None = None
    weight_skills: float = 0.5
    weight_experience: float = 0.3
    weight_education: float = 0.2


class JobOfferUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    required_skills: list[str] | None = None
    required_experience_years: float | None = None
    required_education_level: str | None = None
    weight_skills: float | None = None
    weight_experience: float | None = None
    weight_education: float | None = None
    is_active: bool | None = None


class JobOfferResponse(BaseModel):
    id: UUID
    title: str
    description: str
    salary_min: float | None
    salary_max: float | None
    required_skills: list[str] | None
    required_experience_years: float | None
    required_education_level: str | None
    weight_skills: float
    weight_experience: float
    weight_education: float
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CandidateCreate(BaseModel):
    full_name: str = Field(..., min_length=3)
    phone: str | None = None


class CandidateResponse(BaseModel):
    id: UUID
    user_id: UUID
    full_name: str
    phone: str | None
    cv_path: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApplicationCreate(BaseModel):
    job_offer_id: UUID


class ApplicationUpdate(BaseModel):
    status: str = Field(..., pattern="^(PENDING|REVIEWED|ACCEPTED|REJECTED)$")


class ApplicationResponse(BaseModel):
    id: UUID
    candidate_id: UUID
    job_offer_id: UUID
    cv_file_path: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaginatedJobOffers(BaseModel):
    total: int
    page: int
    size: int
    items: list[JobOfferResponse]


class MyApplicationResponse(BaseModel):
    """Application enriched with job offer details — for the candidate's own list."""
    id: UUID
    job_offer_id: UUID
    candidate_id: UUID
    cv_file_path: str
    status: str
    created_at: datetime
    updated_at: datetime

    # joined job offer fields
    job_title: str
    job_description: str
    job_salary_min: float | None = None
    job_salary_max: float | None = None
    job_required_skills: list[str] | None = None
    job_required_experience_years: float | None = None
    job_required_education_level: str | None = None
    job_is_active: bool

    # optional score data (if scoring has been computed)
    total_score: float | None = None
    skills_score: float | None = None
    experience_score: float | None = None
    education_score: float | None = None

    model_config = {"from_attributes": True}
