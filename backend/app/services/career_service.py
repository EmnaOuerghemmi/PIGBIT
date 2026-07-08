from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.career import CareerPlan
from app.models.user import User
from app.schemas.career import CareerPlanCreate, CareerPlanUpdate


class CareerService:

    async def list_plans(self, db: AsyncSession, status_filter: str | None = None) -> list[dict]:
        query = (
            select(CareerPlan, User.full_name)
            .outerjoin(User, CareerPlan.user_id == User.id)
            .order_by(CareerPlan.created_at.desc())
        )
        if status_filter:
            query = query.where(CareerPlan.status == status_filter)
        rows = (await db.execute(query)).all()
        items: list[dict] = []
        for plan, full_name in rows:
            items.append({
                "id": plan.id,
                "user_id": plan.user_id,
                "current_position": plan.current_position,
                "target_position": plan.target_position,
                "status": plan.status,
                "progress": plan.progress,
                "skills_to_develop": plan.skills_to_develop,
                "notes": plan.notes,
                "target_date": plan.target_date,
                "created_at": plan.created_at,
                "updated_at": plan.updated_at,
                "employee_name": full_name,
            })
        return items

    async def get_stats(self, db: AsyncSession) -> dict:
        rows = (
            await db.execute(select(CareerPlan.status, func.count(CareerPlan.id)).group_by(CareerPlan.status))
        ).all()
        counts = {s: c for s, c in rows}
        return {
            "probation": counts.get("PROBATION", 0),
            "promotions_planned": counts.get("PROMOTION_PLANNED", 0),
            "in_progress": counts.get("IN_PROGRESS", 0),
            "retirements_planned": counts.get("RETIREMENT_PLANNED", 0),
            "total": sum(counts.values()),
        }

    async def create_plan(self, db: AsyncSession, data: CareerPlanCreate) -> CareerPlan:
        plan = CareerPlan(**data.model_dump())
        db.add(plan)
        await db.flush()
        return plan

    async def update_plan(self, db: AsyncSession, plan_id: UUID, data: CareerPlanUpdate) -> CareerPlan:
        plan = (await db.execute(select(CareerPlan).where(CareerPlan.id == plan_id))).scalar_one_or_none()
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Career plan not found")
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(plan, field, value)
        await db.flush()
        return plan

    async def delete_plan(self, db: AsyncSession, plan_id: UUID) -> None:
        plan = (await db.execute(select(CareerPlan).where(CareerPlan.id == plan_id))).scalar_one_or_none()
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Career plan not found")
        await db.delete(plan)
        await db.flush()


career_service = CareerService()
