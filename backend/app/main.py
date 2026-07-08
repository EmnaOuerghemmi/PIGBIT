from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.cache.redis_client import close_redis, get_redis
from app.core.config import settings
from app.db.session import engine, AsyncSessionLocal
from app.db.base import Base
from app.db.init_db import init_superadmin
from app.models import user, recruitment, scoring, interview, career, report, negotiation, budget, employee, notification  # noqa: F401

SUPERADMIN_EMAIL = "emna.ouerghemmi@esprit.tn"
SUPERADMIN_USERNAME = "emna_admin"
SUPERADMIN_PASSWORD = "123Emna?"


async def _interview_expiry_loop():
    """Sweep expired interview invitations every 5 minutes."""
    import asyncio
    from app.services.interview_service import interview_service
    while True:
        try:
            async with AsyncSessionLocal() as db:
                await interview_service.sweep_expired(db)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(f"Interview expiry sweep failed: {exc}")
        await asyncio.sleep(300)  # 5 minutes


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    await get_redis()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)
    # Micro-migration : create_all ne modifie pas les tables existantes.
    # Ajoute la colonne de sync Google Calendar si absente (PostgreSQL).
    try:
        from sqlalchemy import text
        async with engine.begin() as conn:
            await conn.execute(text(
                "ALTER TABLE interview_invitations "
                "ADD COLUMN IF NOT EXISTS google_event_id VARCHAR(255)"
            ))
    except Exception as _mig_exc:  # pragma: no cover - sqlite/tests n'en ont pas besoin
        import logging
        logging.getLogger(__name__).debug(f"google_event_id migration skipped: {_mig_exc}")
    async with AsyncSessionLocal() as db:
        await init_superadmin(db, SUPERADMIN_EMAIL, SUPERADMIN_USERNAME, SUPERADMIN_PASSWORD)
    # Seed de démo Budget/Employés (idempotent) pour que le backoffice affiche
    # des données dès le premier lancement.
    try:
        from app.services.budget_service import budget_service
        from app.services.employee_service import employee_service
        async with AsyncSessionLocal() as db:
            await employee_service.seed_demo_data(db)
            await budget_service.seed_demo_data(db)
            await db.commit()
    except Exception as _seed_exc:  # pragma: no cover - demo data must never block boot
        import logging
        logging.getLogger(__name__).warning(f"Demo seed skipped: {_seed_exc}")
    expiry_task = asyncio.create_task(_interview_expiry_loop())
    yield
    expiry_task.cancel()
    await close_redis()
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS middleware - must be added before routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://localhost:3000",
        "http://127.0.0.1:4200",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin-allow-popups"
    response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
    return response

app.include_router(api_router, prefix="/api/v1")

# Negotiations router carries its own /api/v1/negotiations prefix (+ WebSocket),
# so it is mounted directly rather than under api_router. It pulls in the
# salary-prediction stack (numpy/pandas); guard the import so the core ATS API
# still boots if those optional ML deps are absent.
try:
    from app.api.v1.endpoints import negotiations
    app.include_router(negotiations.router)
except Exception as _exc:  # pragma: no cover - optional dependency guard
    import logging
    logging.getLogger(__name__).warning(
        f"Negotiations module not mounted (optional ML deps missing?): {_exc}"
    )


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "version": settings.APP_VERSION}


@app.options("/{full_path:path}")
async def preflight(full_path: str):
    return {}
