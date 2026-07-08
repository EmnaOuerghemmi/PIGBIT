import uuid
from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class CareerPlan(Base):
    """
    A career-development plan attached to an internal user (employee).
    Backs the backoffice "Gestion de carrière" module.
    """
    __tablename__ = "career_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    current_position = Column(String(200), nullable=True)
    target_position = Column(String(200), nullable=True)
    # PROBATION | IN_PROGRESS | PROMOTION_PLANNED | COMPLETED | RETIREMENT_PLANNED
    status = Column(String(40), default="IN_PROGRESS", nullable=False)
    progress = Column(Float, default=0.0, nullable=False)  # 0..100
    skills_to_develop = Column(Text, nullable=True)         # comma-separated
    notes = Column(Text, nullable=True)
    target_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User")
    __table_args__ = (Index("ix_career_plans_status", "status"),)
