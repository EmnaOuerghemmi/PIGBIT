from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_active_user, require_role
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.agent import AuditLogResponse, PaginatedAuditLogs
from app.schemas.user import (
    PaginatedUsers,
    UserAdminUpdate,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.services.agent_service import user_service
from app.services.report_service import auth_service

router = APIRouter()


# ---------- /me ----------

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: Annotated[User, Depends(get_current_active_user)]):
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_me(
    body: UserUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    user = await user_service.update_me(db, current_user, body)
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Self-service account deletion (profile "Danger zone").
    Soft-deletes the account and revokes the active session. The superadmin
    account is protected and cannot be self-deleted.
    """
    await user_service.soft_delete(db, current_user.id, current_user)
    current_user.refresh_token = None
    current_user.refresh_token_expires_at = None
    await db.commit()


# ---------- Admin: list & create ----------

@router.get(
    "",
    response_model=PaginatedUsers,
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.RH_MANAGER))],
)
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    role: str | None = None,
    ministry: str | None = None,
    is_active: bool | None = None,
    search: str | None = None,
):
    total, users = await user_service.list_users(db, page, size, role, ministry, is_active, search)
    return PaginatedUsers(total=total, page=page, size=size, items=users)


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def create_user(
    body: UserCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    user = await auth_service.register(
        db,
        email=body.email,
        username=body.username,
        password=body.password,
        full_name=body.full_name,
        role=body.role,
        created_by=current_user.id,
    )
    await db.commit()
    await db.refresh(user)
    return user


# ---------- Admin: single user ops ----------

@router.get(
    "/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.RH_MANAGER))],
)
async def get_user(user_id: UUID, db: Annotated[AsyncSession, Depends(get_db)]):
    return await user_service.get_by_id(db, user_id)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def admin_update_user(
    user_id: UUID,
    body: UserAdminUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    user = await user_service.admin_update(db, user_id, body, current_user)
    await db.commit()
    await db.refresh(user)
    return user


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def delete_user(
    user_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await user_service.soft_delete(db, user_id, current_user)
    await db.commit()


# ---------- Audit logs ----------

@router.get(
    "/audit-logs",
    response_model=PaginatedAuditLogs,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def get_audit_logs(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: UUID | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
):
    total, logs = await user_service.get_audit_logs(db, user_id, page, size)
    return PaginatedAuditLogs(total=total, page=page, size=size, items=logs)


@router.get("/me/audit-logs", response_model=PaginatedAuditLogs)
async def get_my_audit_logs(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    total, logs = await user_service.get_audit_logs(db, current_user.id, page, size)
    return PaginatedAuditLogs(total=total, page=page, size=size, items=logs)
