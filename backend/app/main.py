from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.cache.redis_client import close_redis, get_redis
from app.core.config import settings
from app.db.session import engine, AsyncSessionLocal
from app.db.base import Base
from app.db.init_db import init_superadmin
# Peuple Base.metadata avec l'ensemble des tables (cf. app/models/__init__.py).
# Remplace la liste d'imports manuelle qui omettait `agent_log`.
import app.models  # noqa: F401

SUPERADMIN_EMAIL = "emna.ouerghemmi@esprit.tn"
SUPERADMIN_USERNAME = "emna_admin"
SUPERADMIN_PASSWORD = "123Emna?"


async def _verify_schema_is_current(log) -> None:
    """
    Vérifie que la base porte bien la dernière révision Alembic.

    Ne modifie jamais le schéma : en cas d'écart, on journalise une erreur
    explicite plutôt que de « réparer » silencieusement, ce que faisait
    l'ancien `create_all` (source de dérives entre environnements).
    """
    from sqlalchemy import text
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        cfg = Config("alembic.ini")
        head = ScriptDirectory.from_config(cfg).get_current_head()

        async with engine.connect() as conn:
            current = await conn.scalar(text("SELECT version_num FROM alembic_version"))

        if current == head:
            log.info(f"Schéma à jour (révision Alembic {current}).")
        else:
            log.error(
                f"SCHÉMA DÉSYNCHRONISÉ — base en '{current}', code en '{head}'. "
                f"Lancer : alembic upgrade head"
            )
    except Exception as exc:  # pragma: no cover - SQLite/tests, ou table absente
        log.warning(
            f"Contrôle de schéma impossible ({exc}). "
            f"Si la base est vide, lancer : alembic upgrade head"
        )


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
    import logging

    _log = logging.getLogger(__name__)
    await get_redis()

    # ─── Schéma ────────────────────────────────────────────────────────────
    # Le schéma est désormais géré exclusivement par Alembic (`alembic upgrade
    # head`, lancé au démarrage du conteneur). L'application ne crée ni ne
    # modifie plus de table elle-même : on se contente de vérifier que la base
    # est à jour et d'avertir clairement sinon.
    #
    # NB : les tests utilisent SQLite et créent leur schéma via une fixture
    # dédiée (`tests/conftest.py`), ils ne passent pas par ce contrôle.
    await _verify_schema_is_current(_log)

    # pgvector : la colonne `vec` et son index HNSW sont créés par la migration
    # Alembic dédiée, si l'extension est disponible. Ici on ne fait que
    # DÉTECTER le résultat pour aiguiller le service sémantique entre recherche
    # vectorielle native et repli Python — aucun DDL.
    try:
        from sqlalchemy import text
        from app.services.semantic_service import semantic_service
        async with engine.connect() as conn:
            has_vec = await conn.scalar(text(
                "SELECT count(*) FROM information_schema.columns "
                "WHERE table_name='embeddings' AND column_name='vec'"
            ))
        if has_vec:
            semantic_service.pgvector_enabled = True
            _log.info("pgvector actif — recherche sémantique via index vectoriel natif")
        else:
            _log.info("pgvector absent — recherche sémantique en repli Python (cosinus)")
    except Exception as _vec_exc:  # pragma: no cover - SQLite/tests
        _log.debug(f"Détection pgvector ignorée : {_vec_exc}")
    async with AsyncSessionLocal() as db:
        await init_superadmin(db, SUPERADMIN_EMAIL, SUPERADMIN_USERNAME, SUPERADMIN_PASSWORD)
    # Seed de démo Budget/Employés (idempotent) pour que le backoffice affiche
    # des données dès le premier lancement.
    try:
        from app.services.budget_service import budget_service
        from app.services.employee_service import employee_service
        from app.services.cag_service import cag_service
        async with AsyncSessionLocal() as db:
            await employee_service.seed_demo_data(db)
            await budget_service.seed_demo_data(db)
            # Base de connaissances CAG : seed de la FAQ uniquement. L'indexation
            # (cache d'embeddings) est PARESSEUSE — faite au 1er /cag/ask — pour
            # ne pas charger le modèle neuronal (~470 Mo) au démarrage.
            await cag_service.seed_default_kb(db)
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

# ─── CORS ──────────────────────────────────────────────────────────────────
# Les origines viennent de la configuration (ALLOWED_ORIGINS), plus jamais du
# code : un déploiement se fait en renseignant la variable d'environnement,
# sans toucher aux sources.
#   ALLOWED_ORIGINS=https://app.piqbit.tn,https://admin.piqbit.tn
#   ALLOW_LOCALHOST_ORIGINS=false        # <- impératif en production
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    # Développement uniquement : tolère n'importe quel port localhost
    # (previews Angular, second `ng serve`). Désactivé en production.
    allow_origin_regex=(
        r"http://(localhost|127\.0\.0\.1):\d+"
        if settings.ALLOW_LOCALHOST_ORIGINS
        else None
    ),
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
