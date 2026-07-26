from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def client_ip(request: Request) -> str:
    """
    IP réelle de l'appelant.

    Derrière le reverse-proxy nginx, `request.client.host` vaut l'IP du
    conteneur proxy : sans lecture de X-Forwarded-For, tous les utilisateurs
    partageraient le même compteur de limitation.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(scope: str, limit: int, window_seconds: int):
    """
    Fabrique une dépendance FastAPI limitant une route par IP.

    Usage :
        @router.post("/forgot-password",
                     dependencies=[Depends(rate_limit("forgot_password", 3, 600))])

    Renvoie 429 avec un en-tête `Retry-After` quand le quota est dépassé.
    """
    from app.cache.redis_client import hit_rate_limit

    async def _dependency(request: Request) -> None:
        allowed, retry_after = await hit_rate_limit(
            scope, client_ip(request), limit, window_seconds
        )
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    "Trop de tentatives. Réessayez dans "
                    f"{max(retry_after // 60, 1)} minute(s)."
                ),
                headers={"Retry-After": str(retry_after)},
            )

    return _dependency


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise credentials_exception
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    from sqlalchemy import select
    from datetime import datetime

    result = await db.execute(
        select(User).where(User.id == UUID(user_id), User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    if user.is_locked:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Account temporarily locked")

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    return current_user


def require_role(*roles: str):
    """Dependency factory: raises 403 if user role not in allowed roles."""
    async def _check(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.is_superuser:
            return user
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {list(roles)}",
            )
        return user
    return _check


def require_permission(permission: str):
    """Dependency factory: checks granular permission in user.permissions JSON."""
    async def _check(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.is_superuser:
            return user
        perms: dict = user.permissions or {}
        if not perms.get(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission}",
            )
        return user
    return _check


AdminOnly = Depends(require_role(UserRole.ADMIN))
HRManagerOrAbove = Depends(require_role(UserRole.ADMIN, UserRole.RH_MANAGER))
