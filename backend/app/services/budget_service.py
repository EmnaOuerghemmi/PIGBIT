"""
Service « Budget par département » : enveloppes annuelles, dépenses, stats
agrégées pour le dashboard backoffice, et seed de données de démonstration.
Montants en TND.
"""
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.budget import DepartmentBudget, BudgetExpense
from app.models.employee import Employee
from app.schemas.budget import (
    DepartmentBudgetCreate, DepartmentBudgetUpdate, BudgetExpenseCreate,
)


class BudgetService:

    # ── Lecture / stats ───────────────────────────────────────────────────────

    async def get_stats(self, db: AsyncSession, year: int | None = None) -> dict:
        """Stats agrégées par département + totaux, pour le dashboard budget."""
        year = year or datetime.now(timezone.utc).year

        budgets = (
            await db.execute(
                select(DepartmentBudget)
                .where(DepartmentBudget.year == year)
                .order_by(DepartmentBudget.department)
            )
        ).scalars().all()

        # Dépenses agrégées par budget en une requête.
        spent_rows = (
            await db.execute(
                select(
                    BudgetExpense.budget_id,
                    func.coalesce(func.sum(BudgetExpense.amount), 0.0),
                    func.count(BudgetExpense.id),
                )
                .group_by(BudgetExpense.budget_id)
            )
        ).all()
        spent_by_budget = {bid: (total, count) for bid, total, count in spent_rows}

        # Effectif actif par département (croisement avec le module Employés).
        headcount_rows = (
            await db.execute(
                select(Employee.department, func.count(Employee.id))
                .where(Employee.status == "active")
                .group_by(Employee.department)
            )
        ).all()
        headcount = {dept: c for dept, c in headcount_rows}

        departments = []
        total_allocated = total_spent = 0.0
        for b in budgets:
            spent, count = spent_by_budget.get(b.id, (0.0, 0))
            remaining = b.allocated_amount - spent
            utilization = (spent / b.allocated_amount * 100) if b.allocated_amount else 0.0
            total_allocated += b.allocated_amount
            total_spent += spent
            departments.append({
                "id": b.id,
                "department": b.department,
                "year": b.year,
                "allocated_amount": b.allocated_amount,
                "notes": b.notes,
                "spent": round(spent, 2),
                "remaining": round(remaining, 2),
                "utilization": round(utilization, 1),
                "expenses_count": count,
                "headcount": headcount.get(b.department, 0),
            })

        total_remaining = total_allocated - total_spent
        total_utilization = (total_spent / total_allocated * 100) if total_allocated else 0.0
        return {
            "year": year,
            "totals": {
                "allocated": round(total_allocated, 2),
                "spent": round(total_spent, 2),
                "remaining": round(total_remaining, 2),
                "utilization": round(total_utilization, 1),
            },
            "departments": departments,
        }

    async def list_expenses(self, db: AsyncSession, budget_id: UUID) -> list[BudgetExpense]:
        budget = await self._get_budget(db, budget_id)
        rows = (
            await db.execute(
                select(BudgetExpense)
                .where(BudgetExpense.budget_id == budget.id)
                .order_by(BudgetExpense.spent_at.desc())
            )
        ).scalars().all()
        return list(rows)

    # ── Écriture ──────────────────────────────────────────────────────────────

    async def create_budget(self, db: AsyncSession, data: DepartmentBudgetCreate) -> DepartmentBudget:
        existing = (
            await db.execute(
                select(DepartmentBudget).where(
                    DepartmentBudget.department == data.department,
                    DepartmentBudget.year == data.year,
                )
            )
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Budget déjà défini pour {data.department} / {data.year}",
            )
        budget = DepartmentBudget(**data.model_dump())
        db.add(budget)
        await db.flush()
        await db.refresh(budget)
        return budget

    async def update_budget(self, db: AsyncSession, budget_id: UUID, data: DepartmentBudgetUpdate) -> DepartmentBudget:
        budget = await self._get_budget(db, budget_id)
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(budget, field, value)
        await db.flush()
        await db.refresh(budget)
        return budget

    async def delete_budget(self, db: AsyncSession, budget_id: UUID) -> None:
        budget = await self._get_budget(db, budget_id)
        await db.delete(budget)
        await db.flush()

    async def add_expense(self, db: AsyncSession, budget_id: UUID, data: BudgetExpenseCreate) -> BudgetExpense:
        budget = await self._get_budget(db, budget_id)
        expense = BudgetExpense(budget_id=budget.id, **data.model_dump())
        db.add(expense)
        await db.flush()
        await db.refresh(expense)
        return expense

    async def delete_expense(self, db: AsyncSession, expense_id: UUID) -> None:
        expense = (
            await db.execute(select(BudgetExpense).where(BudgetExpense.id == expense_id))
        ).scalar_one_or_none()
        if not expense:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dépense introuvable")
        await db.delete(expense)
        await db.flush()

    async def _get_budget(self, db: AsyncSession, budget_id: UUID) -> DepartmentBudget:
        budget = (
            await db.execute(select(DepartmentBudget).where(DepartmentBudget.id == budget_id))
        ).scalar_one_or_none()
        if not budget:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget introuvable")
        return budget

    # ── Seed de démonstration ────────────────────────────────────────────────

    async def seed_demo_data(self, db: AsyncSession, year: int | None = None) -> int:
        """
        Insère des budgets + dépenses de démo (idempotent : ne fait rien si des
        budgets existent déjà pour l'année). Retourne le nombre de départements créés.
        """
        year = year or datetime.now(timezone.utc).year
        existing = (
            await db.execute(
                select(func.count(DepartmentBudget.id)).where(DepartmentBudget.year == year)
            )
        ).scalar_one()
        if existing:
            return 0

        # (département, alloué annuel TND, [(label, catégorie, montant TND)])
        demo = [
            ("Tech", 520_000, [
                ("Salaires T1 équipe Tech", "SALAIRES", 96_000),
                ("Salaires T2 équipe Tech", "SALAIRES", 102_000),
                ("Recrutement 2 développeurs seniors", "RECRUTEMENT", 14_500),
                ("Licences cloud & CI/CD", "OUTILS", 22_800),
                ("Formation Kubernetes avancé", "FORMATION", 8_400),
            ]),
            ("Data", 260_000, [
                ("Salaires T1 équipe Data", "SALAIRES", 54_000),
                ("Salaires T2 équipe Data", "SALAIRES", 57_000),
                ("Plateforme data warehouse", "OUTILS", 19_500),
                ("Certification ML engineering", "FORMATION", 6_200),
            ]),
            ("RH", 150_000, [
                ("Salaires T1 équipe RH", "SALAIRES", 33_000),
                ("Salaires T2 équipe RH", "SALAIRES", 33_000),
                ("Campagne marque employeur", "RECRUTEMENT", 9_800),
                ("Abonnement ATS / jobboards", "OUTILS", 7_200),
            ]),
            ("Marketing", 120_000, [
                ("Salaires T1 équipe Marketing", "SALAIRES", 27_000),
                ("Campagnes digitales S1", "AUTRE", 18_500),
                ("Outils SEO & analytics", "OUTILS", 5_400),
            ]),
            ("Commercial", 140_000, [
                ("Salaires T1 équipe Commerciale", "SALAIRES", 36_000),
                ("CRM & prospection", "OUTILS", 8_900),
                ("Formation négociation", "FORMATION", 4_300),
            ]),
            ("Finance", 110_000, [
                ("Salaires T1 équipe Finance", "SALAIRES", 30_000),
                ("Logiciel comptabilité & paie", "OUTILS", 9_600),
            ]),
            ("Support", 90_000, [
                ("Salaires T1 équipe Support", "SALAIRES", 21_000),
                ("Outil ticketing", "OUTILS", 4_800),
            ]),
        ]

        for dept, allocated, expenses in demo:
            budget = DepartmentBudget(department=dept, year=year, allocated_amount=allocated)
            db.add(budget)
            await db.flush()
            for label, category, amount in expenses:
                db.add(BudgetExpense(
                    budget_id=budget.id, label=label, category=category, amount=amount,
                ))
        await db.flush()
        return len(demo)


budget_service = BudgetService()
