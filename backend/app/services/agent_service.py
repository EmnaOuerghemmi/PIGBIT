"""User CRUD service — list, get, update, delete, audit logs."""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import AuditLog, User, UserRole
from app.schemas.user import UserAdminUpdate, UserUpdate


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserService:

    async def get_by_id(self, db: AsyncSession, user_id: UUID) -> User:
        result = await db.execute(
            select(User).where(User.id == user_id, User.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")
        return user

    async def list_users(
        self,
        db: AsyncSession,
        page: int = 1,
        size: int = 20,
        role: str | None = None,
        ministry: str | None = None,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> tuple[int, list[User]]:
        query = select(User).where(User.deleted_at.is_(None))

        if role:
            query = query.where(User.role == role)
        if ministry:
            query = query.where(User.ministry == ministry)
        if is_active is not None:
            query = query.where(User.is_active == is_active)
        if search:
            term = f"%{search}%"
            query = query.where(
                User.email.ilike(term) | User.username.ilike(term) | User.full_name.ilike(term)
            )

        count_result = await db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()

        query = query.offset((page - 1) * size).limit(size).order_by(User.created_at.desc())
        result = await db.execute(query)
        return total, list(result.scalars().all())

    async def update_me(self, db: AsyncSession, user: User, data: UserUpdate) -> User:
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(user, field, value)
        user.updated_at = _utcnow()
        await self._log(db, user.id, "USER_UPDATE_SELF", "user", str(user.id))
        return user

    async def admin_update(
        self, db: AsyncSession, user_id: UUID, data: UserAdminUpdate, acting_user: User
    ) -> User:
        user = await self.get_by_id(db, user_id)
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(user, field, value)
        user.updated_by = acting_user.id
        user.updated_at = _utcnow()
        await self._log(db, acting_user.id, "USER_ADMIN_UPDATE", "user", str(user_id))
        return user

    async def soft_delete(self, db: AsyncSession, user_id: UUID, acting_user: User) -> None:
        user = await self.get_by_id(db, user_id)
        if user.is_superuser:
            raise HTTPException(status_code=403, detail="Cannot delete a superuser.")
        user.deleted_at = _utcnow()
        user.is_active = False
        await self._log(db, acting_user.id, "USER_DELETE", "user", str(user_id))

    async def get_audit_logs(
        self,
        db: AsyncSession,
        user_id: UUID | None = None,
        page: int = 1,
        size: int = 50,
    ) -> tuple[int, list[AuditLog]]:
        query = select(AuditLog)
        if user_id:
            query = query.where(AuditLog.user_id == user_id)

        count_result = await db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()

        query = query.order_by(AuditLog.created_at.desc()).offset((page - 1) * size).limit(size)
        result = await db.execute(query)
        return total, list(result.scalars().all())

    async def _log(
        self,
        db: AsyncSession,
        user_id: UUID | None,
        action: str,
        resource: str | None = None,
        resource_id: str | None = None,
        details: dict | None = None,
    ) -> None:
        db.add(AuditLog(
            user_id=user_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            details=details,
        ))


user_service = UserService()
