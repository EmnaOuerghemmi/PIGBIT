import uuid
from sqlalchemy import Column, String, Float, DateTime, Index, func
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class Employee(Base):
    """
    Fiche employé interne (backoffice « Employés »). Distincte de `users`
    (comptes de connexion) : un employé n'a pas forcément de compte.
    Salaire mensuel brut en TND.
    """
    __tablename__ = "employees"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    phone = Column(String(30), nullable=True)
    position = Column(String(150), nullable=True)
    department = Column(String(100), nullable=True, index=True)
    salary = Column(Float, nullable=True)  # TND mensuel brut
    hire_date = Column(DateTime(timezone=True), nullable=True)
    # active | inactive | on-leave
    status = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (Index("ix_employees_dept_status", "department", "status"),)
