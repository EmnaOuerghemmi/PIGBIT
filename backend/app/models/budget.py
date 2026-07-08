import uuid
from sqlalchemy import Column, String, Text, Float, Integer, DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class DepartmentBudget(Base):
    """
    Enveloppe budgétaire annuelle d'un département (backoffice « Budget »).
    Montants en TND. Le consommé est dérivé des lignes `budget_expenses`.
    """
    __tablename__ = "department_budgets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    department = Column(String(100), nullable=False, index=True)
    year = Column(Integer, nullable=False)
    allocated_amount = Column(Float, nullable=False, default=0.0)  # TND
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    expenses = relationship(
        "BudgetExpense", back_populates="budget", cascade="all, delete-orphan",
        order_by="BudgetExpense.spent_at",
    )
    __table_args__ = (
        Index("ix_department_budgets_dept_year", "department", "year", unique=True),
    )


class BudgetExpense(Base):
    """Ligne de dépense imputée sur le budget d'un département."""
    __tablename__ = "budget_expenses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    budget_id = Column(
        UUID(as_uuid=True),
        ForeignKey("department_budgets.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    label = Column(String(200), nullable=False)
    # SALAIRES | RECRUTEMENT | FORMATION | OUTILS | AUTRE
    category = Column(String(40), nullable=False, default="AUTRE")
    amount = Column(Float, nullable=False)  # TND
    spent_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    budget = relationship("DepartmentBudget", back_populates="expenses")
