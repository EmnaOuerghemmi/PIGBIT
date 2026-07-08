from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User, UserRole


async def init_superadmin(db: AsyncSession, email: str, username: str, password: str) -> User | None:
    """Creates the superadmin user if it does not already exist."""
    from sqlalchemy import select

    result = await db.execute(select(User).where(User.email == email))
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    user = User(
        email=email,
        username=username,
        hashed_password=hash_password(password),
        is_active=True,
        is_superuser=True,
        is_verified=True,
        role=UserRole.ADMIN,
        full_name="Super Admin",
        permissions={},
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
