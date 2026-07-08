"""
Service « Employés » : CRUD des fiches employés internes + seed de démo.
Alimente aussi l'effectif (headcount) du dashboard Budget par département.
"""
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.employee import Employee
from app.schemas.employee import EmployeeCreate, EmployeeUpdate


class EmployeeService:

    async def list_employees(
        self, db: AsyncSession, department: str | None = None, status_filter: str | None = None,
    ) -> list[Employee]:
        query = select(Employee).order_by(Employee.last_name, Employee.first_name)
        if department:
            query = query.where(Employee.department == department)
        if status_filter:
            query = query.where(Employee.status == status_filter)
        return list((await db.execute(query)).scalars().all())

    async def get_employee(self, db: AsyncSession, employee_id: UUID) -> Employee:
        employee = (
            await db.execute(select(Employee).where(Employee.id == employee_id))
        ).scalar_one_or_none()
        if not employee:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employé introuvable")
        return employee

    async def create_employee(self, db: AsyncSession, data: EmployeeCreate) -> Employee:
        duplicate = (
            await db.execute(select(Employee).where(Employee.email == data.email))
        ).scalar_one_or_none()
        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Un employé existe déjà avec cet email",
            )
        employee = Employee(**data.model_dump())
        db.add(employee)
        await db.flush()
        await db.refresh(employee)
        return employee

    async def update_employee(self, db: AsyncSession, employee_id: UUID, data: EmployeeUpdate) -> Employee:
        employee = await self.get_employee(db, employee_id)
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(employee, field, value)
        await db.flush()
        await db.refresh(employee)
        return employee

    async def delete_employee(self, db: AsyncSession, employee_id: UUID) -> None:
        employee = await self.get_employee(db, employee_id)
        await db.delete(employee)
        await db.flush()

    # ── Seed de démonstration ────────────────────────────────────────────────

    async def seed_demo_data(self, db: AsyncSession) -> int:
        """Insère des employés de démo (idempotent : ne fait rien si la table est remplie)."""
        existing = (await db.execute(select(func.count(Employee.id)))).scalar_one()
        if existing:
            return 0

        def d(year: int, month: int, day: int) -> datetime:
            return datetime(year, month, day, tzinfo=timezone.utc)

        demo = [
            # (prénom, nom, email, poste, département, salaire TND/mois, embauche, statut)
            ("Ahmed", "Ben Salah", "ahmed.bensalah@piqbit.tn", "Lead Backend Developer", "Tech", 4600, d(2021, 3, 1), "active"),
            ("Ines", "Trabelsi", "ines.trabelsi@piqbit.tn", "Frontend Developer", "Tech", 2350, d(2023, 9, 15), "active"),
            ("Mohamed", "Gharbi", "mohamed.gharbi@piqbit.tn", "DevOps Engineer", "Tech", 3400, d(2022, 5, 2), "active"),
            ("Sara", "Mansouri", "sara.mansouri@piqbit.tn", "QA Engineer", "Tech", 2100, d(2024, 1, 8), "on-leave"),
            ("Yassine", "Karray", "yassine.karray@piqbit.tn", "Senior Data Scientist", "Data", 4700, d(2021, 11, 22), "active"),
            ("Rim", "Chaabane", "rim.chaabane@piqbit.tn", "Data Analyst", "Data", 2250, d(2023, 4, 3), "active"),
            ("Emna", "Ouerghemmi", "emna.ouerghemmi@piqbit.tn", "HR Manager", "RH", 3800, d(2020, 9, 1), "active"),
            ("Khalil", "Jebali", "khalil.jebali@piqbit.tn", "Talent Acquisition Specialist", "RH", 2200, d(2023, 2, 13), "active"),
            ("Nour", "Baccouche", "nour.baccouche@piqbit.tn", "Digital Marketing Specialist", "Marketing", 2050, d(2023, 6, 19), "active"),
            ("Aymen", "Sassi", "aymen.sassi@piqbit.tn", "Account Manager", "Commercial", 2600, d(2022, 10, 4), "active"),
            ("Salma", "Dridi", "salma.dridi@piqbit.tn", "Comptable Senior", "Finance", 2500, d(2021, 7, 12), "active"),
            ("Oussama", "Maaloul", "oussama.maaloul@piqbit.tn", "Customer Success Agent", "Support", 1750, d(2024, 3, 25), "inactive"),
        ]
        for first, last, email, position, dept, salary, hired, st in demo:
            db.add(Employee(
                first_name=first, last_name=last, email=email, position=position,
                department=dept, salary=salary, hire_date=hired, status=st,
            ))
        await db.flush()
        return len(demo)


employee_service = EmployeeService()
