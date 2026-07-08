from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class BudgetExpenseCreate(BaseModel):
    label: str = Field(..., max_length=200)
    category: str = Field(default="AUTRE", max_length=40)
    amount: float = Field(..., gt=0)


class BudgetExpenseResponse(BaseModel):
    id: UUID
    label: str
    category: str
    amount: float
    spent_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class DepartmentBudgetCreate(BaseModel):
    department: str = Field(..., max_length=100)
    year: int = Field(..., ge=2000, le=2100)
    allocated_amount: float = Field(..., ge=0)
    notes: str | None = None


class DepartmentBudgetUpdate(BaseModel):
    allocated_amount: float | None = Field(default=None, ge=0)
    notes: str | None = None


class DepartmentBudgetResponse(BaseModel):
    id: UUID
    department: str
    year: int
    allocated_amount: float
    notes: str | None = None
    spent: float = 0.0
    remaining: float = 0.0
    utilization: float = 0.0  # 0..100
    expenses_count: int = 0
    headcount: int = 0

    model_config = ConfigDict(from_attributes=True)


class BudgetTotals(BaseModel):
    allocated: float
    spent: float
    remaining: float
    utilization: float  # 0..100


class BudgetStats(BaseModel):
    year: int
    totals: BudgetTotals
    departments: list[DepartmentBudgetResponse]
