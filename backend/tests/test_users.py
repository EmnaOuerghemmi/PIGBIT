"""User CRUD and permission tests."""
import pytest
from httpx import AsyncClient

from tests.conftest import VALID_PASSWORD, USER_PAYLOAD


ADMIN_PAYLOAD = {
    "email": "admin@example.com",
    "username": "adminuser",
    "password": VALID_PASSWORD,
    "full_name": "Admin User",
}


async def _register_and_login(client: AsyncClient, payload: dict) -> str:
    await client.post("/api/v1/auth/register", json=payload)
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    return resp.json()["access_token"]


# ---------- /me ----------

@pytest.mark.asyncio
async def test_get_me(client: AsyncClient):
    token = await _register_and_login(client, USER_PAYLOAD)
    resp = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == USER_PAYLOAD["email"]


@pytest.mark.asyncio
async def test_get_me_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_update_me(client: AsyncClient):
    token = await _register_and_login(client, USER_PAYLOAD)
    resp = await client.patch(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"full_name": "Updated Name", "language": "ar"},
    )
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Updated Name"
    assert resp.json()["language"] == "ar"


# ---------- Role-based access ----------

@pytest.mark.asyncio
async def test_list_users_forbidden_for_read_only(client: AsyncClient):
    """READ_ONLY user must get 403 on the users list."""
    token = await _register_and_login(client, USER_PAYLOAD)
    resp = await client.get(
        "/api/v1/users", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_user_forbidden_for_non_admin(client: AsyncClient):
    token = await _register_and_login(client, USER_PAYLOAD)
    resp = await client.delete(
        "/api/v1/users/00000000-0000-0000-0000-000000000001",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


# ---------- Audit logs ----------

@pytest.mark.asyncio
async def test_my_audit_logs(client: AsyncClient):
    token = await _register_and_login(client, USER_PAYLOAD)
    resp = await client.get(
        "/api/v1/users/me/audit-logs",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data


# ---------- Admin audit logs requires ADMIN role ----------

@pytest.mark.asyncio
async def test_admin_audit_logs_forbidden(client: AsyncClient):
    token = await _register_and_login(client, USER_PAYLOAD)
    resp = await client.get(
        "/api/v1/users/audit-logs",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
