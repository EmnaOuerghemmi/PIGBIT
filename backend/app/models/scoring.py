import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey, Index, Boolean, Integer, func, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class CVAnalysis(Base):
    __tablename__ = "cv_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"), nullable=False, unique=True)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False)
    raw_text = Column(Text, nullable=True)
    extracted_skills = Column(JSON, nullable=False, default=list)
    extracted_experience_years = Column(Float, nullable=True)
    extracted_education_level = Column(String(20), nullable=True)
    extracted_job_titles = Column(JSON, nullable=False, default=list)
    extracted_keywords = Column(JSON, nullable=False, default=list)
    is_parsed = Column(Boolean, default=False, nullable=False)
    parsed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_cv_analyses_application_id", "application_id"),
        Index("ix_cv_analyses_candidate_id", "candidate_id"),
    )


class CandidateScore(Base):
    __tablename__ = "candidate_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"), nullable=False, unique=True)
    job_offer_id = Column(UUID(as_uuid=True), ForeignKey("job_offers.id"), nullable=False)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False)
    total_score = Column(Float, nullable=False)
    skills_score = Column(Float, nullable=False)
    experience_score = Column(Float, nullable=False)
    education_score = Column(Float, nullable=False)
    rank = Column(Integer, nullable=True)
    score_details = Column(JSON, nullable=True)
    computed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_candidate_scores_application_id", "application_id"),
        Index("ix_candidate_scores_job_offer_id", "job_offer_id"),
        Index("ix_candidate_scores_candidate_id", "candidate_id"),
        Index("ix_candidate_scores_job_rank", "job_offer_id", "rank"),
    )
