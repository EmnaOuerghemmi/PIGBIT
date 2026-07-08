from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class CVAnalysisResponse(BaseModel):
    id: UUID
    application_id: UUID
    candidate_id: UUID
    extracted_skills: list[str]
    extracted_experience_years: float | None
    extracted_education_level: str
    extracted_job_titles: list[str]
    extracted_keywords: list[str]
    is_parsed: bool
    parsed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ScoreDetailsResponse(BaseModel):
    matched_skills: list[str]
    missing_skills: list[str] = []
    required_skills: list[str] | None
    extracted_years: float | None
    required_years: float | None
    extracted_education: str | None
    required_education: str | None
    weights: dict
    strengths: list[str] = []
    weaknesses: list[str] = []
    recommendation: str = ""


class CandidateScoreResponse(BaseModel):
    id: UUID
    application_id: UUID
    job_offer_id: UUID
    candidate_id: UUID
    total_score: float = Field(..., ge=0, le=100)
    skills_score: float = Field(..., ge=0, le=100)
    experience_score: float = Field(..., ge=0, le=100)
    education_score: float = Field(..., ge=0, le=100)
    rank: int | None
    score_details: dict | None
    computed_at: datetime

    model_config = {"from_attributes": True}


class CandidateRankingItem(BaseModel):
    candidate_id: UUID
    application_id: UUID
    total_score: float = Field(..., ge=0, le=100)
    rank: int | None
    skills_score: float
    experience_score: float
    education_score: float
    score_details: dict | None
    # Active interview-invitation status for this candidate. Lets the UI
    # disable / relabel the "Planifier Entretien" button without an extra
    # round-trip per row.
    interview_status: str | None = None  # PENDING | CONFIRMED | None
    interview_invitation_id: UUID | None = None
    interview_confirmed_at: datetime | None = None


class JobRankingResponse(BaseModel):
    job_offer_id: UUID
    total_candidates: int
    ranking: list[CandidateRankingItem]


class AnalysisStartedResponse(BaseModel):
    message: str
    application_id: UUID | None = None
    job_id: UUID | None = None


class BulkAnalysisResponse(BaseModel):
    message: str
    job_id: UUID
    count_queued: int
