import uuid
from sqlalchemy import Column, String, Text, Float, Integer, DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class Negotiation(Base):
    """
    Persisted salary negotiation between the platform (candidate side) and an
    employer. Replaces the previous in-memory `DecisionService.negotiations`
    dict so that negotiations survive a server restart and stay auditable.

    A negotiation groups an ordered list of `NegotiationRound` entries (the
    exchange of offers / counter-offers) and keeps the final outcome.
    """
    __tablename__ = "negotiations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Business key used by the WebSocket / summary endpoints (usually the job id).
    job_id = Column(String(100), nullable=False, index=True)
    candidate_id = Column(String(100), nullable=False)
    # Optional FK links when the ids match real rows (kept nullable so the
    # negotiation engine can run on ad-hoc job_data too).
    job_offer_id = Column(UUID(as_uuid=True), ForeignKey("job_offers.id", ondelete="SET NULL"), nullable=True)

    predicted_salary = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)
    initial_offer = Column(Float, nullable=False)
    final_salary = Column(Float, nullable=True)
    # PENDING | ONGOING | ACCEPTED | REJECTED | COMPROMIS
    status = Column(String(20), default="PENDING", nullable=False, index=True)
    reason = Column(Text, nullable=True)
    rounds_count = Column(Integer, default=0, nullable=False)
    max_iterations = Column(Integer, default=5, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    rounds = relationship(
        "NegotiationRound",
        back_populates="negotiation",
        cascade="all, delete-orphan",
        order_by="NegotiationRound.round_number",
    )

    __table_args__ = (
        Index("ix_negotiations_job_status", "job_id", "status"),
    )


class NegotiationRound(Base):
    """
    A single exchange within a negotiation: who acted (candidate/employer),
    the amount put on the table, the resulting decision and its justification.
    """
    __tablename__ = "negotiation_rounds"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    negotiation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("negotiations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    round_number = Column(Integer, nullable=False)
    # candidate | employer | system
    actor = Column(String(20), nullable=False)
    amount = Column(Float, nullable=True)
    # accept | reject | counter_offer | pending
    decision = Column(String(20), nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    negotiation = relationship("Negotiation", back_populates="rounds")

    __table_args__ = (
        Index("ix_negotiation_rounds_neg_round", "negotiation_id", "round_number"),
    )
