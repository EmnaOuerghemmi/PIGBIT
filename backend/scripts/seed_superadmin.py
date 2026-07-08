"""
Run: python -m scripts.seed_superadmin
Creates the superadmin user if not already present.
"""
import asyncio
import sys
import os

# psycopg3 async requires SelectorEventLoop on Windows (not ProactorEventLoop)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.session import AsyncSessionLocal
from app.db.init_db import init_superadmin


SUPERADMIN_EMAIL = "emna.ouerghemmi@esprit.tn"
SUPERADMIN_USERNAME = "emna_admin"
SUPERADMIN_PASSWORD = "123Emna?"


async def main() -> None:
    from app.db.session import engine
    from app.db.base import Base
    from app.models.user import User, AuditLog  # noqa: F401 — register models with Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        user = await init_superadmin(
            db,
            email=SUPERADMIN_EMAIL,
            username=SUPERADMIN_USERNAME,
            password=SUPERADMIN_PASSWORD,
        )
        if user:
            print(f"[OK] SuperAdmin ready: {user.email} (id={user.id})")
        else:
            print("[SKIP] SuperAdmin already exists.")


if __name__ == "__main__":
    asyncio.run(main())
