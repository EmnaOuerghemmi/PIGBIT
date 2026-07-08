"""
Tests for the V1 features added on top of the base ATS:
  - CAND-08  DELETE /recruitment/applications/{id}
  - OFF      PUT    /recruitment/jobs/{id}
  - Profile  DELETE /users/me
  - Saved jobs CRUD
  - Career / Reports / Decision modules (RBAC + happy path)
  - Applications CSV export

They follow the same sqlite + ASGITransport setup as test_auth / test_users.
"""
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.core.security import hash_password
from tests.conftest import VALID_PASSWORD, USER_PAYLOAD


async def _register_and_login(client: AsyncClient, payload: dict) -> str:
    await client.post("/api/v1/auth/register", json=payload)
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    return resp.json()["access_token"]


async def _make_admin_token(client: AsyncClient, db: AsyncSession) -> str:
    """Insert an ADMIN user directly, then log in to get a token."""
    admin = User(
        id=uuid.uuid4(),
        email="admin_extra@example.com",
        username="admin_extra",
        hashed_password=hash_password(VALID_PASSWORD),
        full_name="Admin Extra",
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
    )
    db.add(admin)
    await db.commit()
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin_extra@example.com", "password": VALID_PASSWORD},
    )
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Saved jobs ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_saved_jobs_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/recruitment/saved-jobs")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_saved_jobs_full_flow(client: AsyncClient, db: AsyncSession):
    admin_token = await _make_admin_token(client, db)
    user_token = await _register_and_login(client, USER_PAYLOAD)

    # Admin creates a job
    job_resp = await client.post(
        "/api/v1/recruitment/jobs",
        headers=_auth(admin_token),
        json={"title": "Backend Dev", "description": "Build APIs with FastAPI."},
    )
    assert job_resp.status_code == 201
    job_id = job_resp.json()["id"]

    # User saves it
    save_resp = await client.post(f"/api/v1/recruitment/saved-jobs/{job_id}", headers=_auth(user_token))
    assert save_resp.status_code == 201

    # User lists saved jobs → contains it
    list_resp = await client.get("/api/v1/recruitment/saved-jobs", headers=_auth(user_token))
    assert list_resp.status_code == 200
    assert any(j["id"] == job_id for j in list_resp.json())

    # User unsaves it → list empty
    unsave_resp = await client.delete(f"/api/v1/recruitment/saved-jobs/{job_id}", headers=_auth(user_token))
    assert unsave_resp.status_code == 204
    list_resp2 = await client.get("/api/v1/recruitment/saved-jobs", headers=_auth(user_token))
    assert list_resp2.json() == []


# ── Job PUT (full update) ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_put_job_requires_role(client: AsyncClient):
    token = await _register_and_login(client, USER_PAYLOAD)
    resp = await client.put(
        f"/api/v1/recruitment/jobs/{uuid.uuid4()}",
        headers=_auth(token),
        json={"title": "x", "description": "y"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_put_job_admin_updates(client: AsyncClient, db: AsyncSession):
    admin_token = await _make_admin_token(client, db)
    job = (await client.post(
        "/api/v1/recruitment/jobs",
        headers=_auth(admin_token),
        json={"title": "Old title", "description": "Old description here."},
    )).json()
    resp = await client.put(
        f"/api/v1/recruitment/jobs/{job['id']}",
        headers=_auth(admin_token),
        json={"title": "New title", "description": "Brand new description."},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "New title"


# ── Application deletion (CAND-08) ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_application_requires_admin(client: AsyncClient):
    token = await _register_and_login(client, USER_PAYLOAD)
    resp = await client.delete(
        f"/api/v1/recruitment/applications/{uuid.uuid4()}",
        headers=_auth(token),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_application_admin_404_when_missing(client: AsyncClient, db: AsyncSession):
    admin_token = await _make_admin_token(client, db)
    resp = await client.delete(
        f"/api/v1/recruitment/applications/{uuid.uuid4()}",
        headers=_auth(admin_token),
    )
    assert resp.status_code == 404


# ── Export ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_export_requires_role(client: AsyncClient):
    token = await _register_and_login(client, USER_PAYLOAD)
    resp = await client.get("/api/v1/recruitment/applications/export", headers=_auth(token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_export_admin_csv(client: AsyncClient, db: AsyncSession):
    admin_token = await _make_admin_token(client, db)
    resp = await client.get("/api/v1/recruitment/applications/export", headers=_auth(admin_token))
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "candidate_name" in resp.text


# ── Account deletion (profile danger zone) ───────────────────────────────────

@pytest.mark.asyncio
async def test_delete_own_account(client: AsyncClient):
    token = await _register_and_login(client, USER_PAYLOAD)
    resp = await client.delete("/api/v1/users/me", headers=_auth(token))
    assert resp.status_code == 204
    # The account is now soft-deleted → the token no longer resolves a user.
    me = await client.get("/api/v1/users/me", headers=_auth(token))
    assert me.status_code == 401


# ── Career module ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_career_stats_requires_role(client: AsyncClient):
    token = await _register_and_login(client, USER_PAYLOAD)
    resp = await client.get("/api/v1/career/stats", headers=_auth(token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_career_stats_admin(client: AsyncClient, db: AsyncSession):
    admin_token = await _make_admin_token(client, db)
    resp = await client.get("/api/v1/career/stats", headers=_auth(admin_token))
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


# ── Reports module ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reports_summary_admin(client: AsyncClient, db: AsyncSession):
    admin_token = await _make_admin_token(client, db)
    resp = await client.get("/api/v1/reports/recruitment-summary", headers=_auth(admin_token))
    assert resp.status_code == 200
    body = resp.json()
    assert "total_jobs" in body and "applications_by_status" in body


# ── Decision module ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_decision_evaluate_offer(client: AsyncClient, db: AsyncSession):
    admin_token = await _make_admin_token(client, db)
    resp = await client.post(
        "/api/v1/decision/evaluate-offer",
        headers=_auth(admin_token),
        json={"predicted_salary": 100, "offered_salary": 99, "confidence": 0.9},
    )
    assert resp.status_code == 200
    assert resp.json()["decision"] in {"accept", "counter_offer", "reject"}
