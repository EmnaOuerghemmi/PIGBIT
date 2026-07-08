import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, func
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class ReportSnapshot(Base):
    """
    A persisted snapshot of an analytics report (recruitment KPIs at a point
    in time). Lets RH archive and compare reports over time.
    """
    __tablename__ = "report_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_type = Column(String(50), nullable=False, default="recruitment_summary")
    title = Column(String(200), nullable=True)
    data = Column(JSON, nullable=False, default=dict)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
