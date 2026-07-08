import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey, Index, Boolean, func, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class JobOffer(Base):
    __tablename__ = "job_offers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=False)
    salary_min = Column(Float, nullable=True)
    salary_max = Column(Float, nullable=True)
    required_skills = Column(JSON, nullable=True, default=list)
    required_experience_years = Column(Float, nullable=True)
    required_education_level = Column(String(20), nullable=True)
    weight_skills = Column(Float, default=0.5, nullable=False)
    weight_experience = Column(Float, default=0.3, nullable=False)
    weight_education = Column(Float, default=0.2, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    applications = relationship("Application", back_populates="job_offer", cascade="all, delete-orphan")
    __table_args__ = (Index("ix_job_offers_active_created", "is_active", "created_at"),)


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(30), nullable=True)
    cv_path = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="candidate")
    applications = relationship("Application", back_populates="candidate", cascade="all, delete-orphan")
    __table_args__ = (Index("ix_candidates_user_id", "user_id"),)


class SavedJob(Base):
    """A job offer bookmarked by a user (frontoffice "Offres sauvegardées")."""
    __tablename__ = "saved_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    job_offer_id = Column(UUID(as_uuid=True), ForeignKey("job_offers.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    job_offer = relationship("JobOffer")
    __table_args__ = (
        Index("ix_saved_jobs_user_job", "user_id", "job_offer_id", unique=True),
    )


class Application(Base):
    __tablename__ = "applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False)
    job_offer_id = Column(UUID(as_uuid=True), ForeignKey("job_offers.id"), nullable=False)
    cv_file_path = Column(String(500), nullable=False)
    status = Column(String(50), default="PENDING", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    candidate = relationship("Candidate", back_populates="applications")
    job_offer = relationship("JobOffer", back_populates="applications")
    __table_args__ = (
        Index("ix_applications_candidate_job", "candidate_id", "job_offer_id"),
        Index("ix_applications_status", "status"),
    )
