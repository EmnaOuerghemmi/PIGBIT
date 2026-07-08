"""
Tests des modules Budget par département et Employés (V1.2) :
  - seed idempotent (budgets + employés)
  - stats agrégées (alloué / dépensé / restant / utilisation / headcount)
  - CRUD dépenses et employés (avec contrat camelCase du frontend)
  - RBAC : accès refusé sans token / pour un candidat READ_ONLY

Même setup sqlite + ASGITransport que les autres tests.
"""
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User, UserRole
from app.services.budget_service import budget_service
from app.services.employee_service import employee_service
from tests.conftest import VALID_PASSWORD, USER_PAYLOAD


async def _make_admin_token(client: AsyncClient, db: AsyncSession) -> str:
    admin = User(
        id=uuid.uuid4(),
        email="admin_budget@example.com",
        username="admin_budget",
        hashed_password=hash_password(VALID_PASSWORD),
        full_name="Admin Budget",
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
    )
    db.add(admin)
    await db.commit()
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin_budget@example.com", "password": VALID_PASSWORD},
    )
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Services / seed ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_seed_budget_idempotent(db: AsyncSession):
    first = await budget_service.seed_demo_data(db, year=2026)
    second = await budget_service.seed_demo_data(db, year=2026)
    assert first > 0
    assert second == 0  # idempotent


@pytest.mark.asyncio
async def test_seed_employees_idempotent(db: AsyncSession):
    first = await employee_service.seed_demo_data(db)
    second = await employee_service.seed_demo_data(db)
    assert first > 0
    assert second == 0


@pytest.mark.asyncio
async def test_budget_stats_aggregation(db: AsyncSession):
    await employee_service.seed_demo_data(db)
    await budget_service.seed_demo_data(db, year=2026)

    stats = await budget_service.get_stats(db, year=2026)
    assert stats["year"] == 2026
    assert len(stats["departments"]) >= 5

    totals = stats["totals"]
    assert totals["allocated"] > 0
    assert totals["spent"] > 0
    assert abs(totals["remaining"] - (totals["allocated"] - totals["spent"])) < 0.01
    assert 0 < totals["utilization"] < 100

    tech = next(d for d in stats["departments"] if d["department"] == "Tech")
    assert tech["allocated_amount"] > 0
    assert tech["spent"] > 0
    assert tech["expenses_count"] > 0
    # Croisement avec le module Employés : effectif actif Tech du seed = 3
    # (4 employés Tech dont 1 en congé).
    assert tech["headcount"] == 3


# ── API Budget ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_budget_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/budget/stats")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_budget_forbidden_for_candidate(client: AsyncClient):
    await client.post("/api/v1/auth/register", json=USER_PAYLOAD)
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": USER_PAYLOAD["email"], "password": USER_PAYLOAD["password"]},
    )
    token = login.json()["access_token"]
    resp = await client.get("/api/v1/budget/stats", headers=_auth(token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_budget_stats_and_expense_flow(client: AsyncClient, db: AsyncSession):
    token = await _make_admin_token(client, db)

    # Seed via l'endpoint puis lecture des stats.
    seed = await client.post("/api/v1/budget/seed", headers=_auth(token))
    assert seed.status_code == 201
    stats = await client.get("/api/v1/budget/stats", headers=_auth(token))
    assert stats.status_code == 200
    data = stats.json()
    assert data["departments"], data

    dept = data["departments"][0]
    before_spent = dept["spent"]

    # Ajout d'une dépense → le consommé augmente.
    add = await client.post(
        f"/api/v1/budget/departments/{dept['id']}/expenses",
        json={"label": "Test dépense", "category": "OUTILS", "amount": 1000},
        headers=_auth(token),
    )
    assert add.status_code == 201, add.text
    expense_id = add.json()["id"]

    stats2 = (await client.get("/api/v1/budget/stats", headers=_auth(token))).json()
    dept2 = next(d for d in stats2["departments"] if d["id"] == dept["id"])
    assert dept2["spent"] == pytest.approx(before_spent + 1000)

    # Suppression de la dépense → retour à l'état initial.
    dele = await client.delete(f"/api/v1/budget/expenses/{expense_id}", headers=_auth(token))
    assert dele.status_code == 204
    stats3 = (await client.get("/api/v1/budget/stats", headers=_auth(token))).json()
    dept3 = next(d for d in stats3["departments"] if d["id"] == dept["id"])
    assert dept3["spent"] == pytest.approx(before_spent)


# ── API Employés ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_employees_crud_camelcase_contract(client: AsyncClient, db: AsyncSession):
    token = await _make_admin_token(client, db)

    # Création avec le payload camelCase envoyé par le frontend Angular.
    create = await client.post(
        "/api/v1/employees",
        json={
            "firstName": "Test", "lastName": "Employe",
            "email": "test.employe@piqbit.tn",
            "position": "QA Engineer", "department": "Tech",
            "salary": 2100, "status": "active",
        },
        headers=_auth(token),
    )
    assert create.status_code == 201, create.text
    created = create.json()
    # La réponse doit être en camelCase (contrat du modèle Angular).
    assert created["firstName"] == "Test"
    assert created["lastName"] == "Employe"
    emp_id = created["id"]

    # Email dupliqué → 409.
    dup = await client.post(
        "/api/v1/employees",
        json={"firstName": "X", "lastName": "Y", "email": "test.employe@piqbit.tn"},
        headers=_auth(token),
    )
    assert dup.status_code == 409

    # Liste + filtre département.
    listing = await client.get("/api/v1/employees?department=Tech", headers=_auth(token))
    assert listing.status_code == 200
    assert any(e["id"] == emp_id for e in listing.json())

    # Mise à jour (PUT) partielle.
    update = await client.put(
        f"/api/v1/employees/{emp_id}",
        json={"salary": 2400, "status": "on-leave"},
        headers=_auth(token),
    )
    assert update.status_code == 200
    assert update.json()["salary"] == 2400
    assert update.json()["status"] == "on-leave"

    # Suppression puis 404.
    dele = await client.delete(f"/api/v1/employees/{emp_id}", headers=_auth(token))
    assert dele.status_code == 204
    gone = await client.get(f"/api/v1/employees/{emp_id}", headers=_auth(token))
    assert gone.status_code == 404


@pytest.mark.asyncio
async def test_employees_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/employees")
    assert resp.status_code == 401
