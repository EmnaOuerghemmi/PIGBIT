import os

# Backend d'embedding déterministe et hors-ligne pour les tests : le hash
# fallback évite le téléchargement du modèle sentence-transformers (~470 Mo)
# et rend les similarités reproductibles. À poser AVANT l'import de l'app.
os.environ.setdefault("EMBEDDINGS_BACKEND", "hash")

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_db
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# NullPool : pytest-asyncio (>=1.x) exécute chaque test dans son propre event
# loop ; des connexions poolées créées sur la loop d'un test précédent
# provoqueraient « RuntimeError: Event loop is closed ».
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest_asyncio.fixture(autouse=True)
async def _fresh_redis():
    """
    Le client Redis global se lie à l'event loop qui l'a créé. Comme chaque
    test tourne dans sa propre loop, on repart d'un client neuf par test
    (sinon : « Event loop is closed » dès le 2e login de la session).

    On purge aussi les compteurs anti-bruteforce (`login_attempts:*`) : les
    tests de mot de passe erroné les incrémentent dans le vrai Redis (TTL
    15 min) et pollueraient sinon les logins des tests suivants (429).
    """
    from app.cache import redis_client
    redis_client._redis = None
    try:
        r = await redis_client.get_redis()
        keys = await r.keys("login_attempts:*")
        if keys:
            await r.delete(*keys)
    except Exception:
        redis_client._redis = None
    yield
    try:
        await redis_client.close_redis()
    except Exception:
        redis_client._redis = None


@pytest_asyncio.fixture(scope="function")
async def db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestSessionLocal() as session:
        yield session
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db: AsyncSession):
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


VALID_PASSWORD = "Test1234!"
WEAK_PASSWORD = "weak"
SUPERADMIN_EMAIL = "emna.ouerghemmi@esprit.tn"
SUPERADMIN_PASSWORD = "123Emna?"

USER_PAYLOAD = {
    "email": "testuser@example.com",
    "username": "testuser",
    "password": VALID_PASSWORD,
    "full_name": "Test User",
}
