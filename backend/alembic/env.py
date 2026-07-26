from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context
from app.db.base import Base
from app.core.config import settings

# IMPORT CRITIQUE : peuple `Base.metadata` avec les 22 tables. Sans lui, la
# metadata est vide et l'autogenerate produit une migration qui DROP tout le
# schéma (l'écart détecté étant « la base a des tables, le code n'en déclare
# aucune »). Ne pas retirer, même si un linter le signale comme inutilisé.
import app.models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_sync_url() -> str:
    """
    L'application tourne en asyncpg, mais Alembic pilote un moteur SYNCHRONE.
    Passer l'URL `postgresql+asyncpg://` telle quelle à `engine_from_config`
    lève `InvalidRequestError: The asyncio extension requires an async driver`.
    On bascule donc vers psycopg2 (déjà présent dans les dépendances) pour
    les migrations uniquement — l'app, elle, garde asyncpg.
    """
    url = settings.DATABASE_URL
    return url.replace("+asyncpg", "+psycopg2").replace("+aiosqlite", "")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=get_sync_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_sync_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Détecte aussi les changements de type et de valeur par défaut,
            # que l'autogenerate ignore silencieusement sinon.
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
