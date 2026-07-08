"""
Tests du module Rapports complété (V1.3) :
  - agent de reporting (narrative / highlights / recommandations, fallback déterministe)
  - POST /reports/snapshot : contenu de l'agent inclus dans le snapshot
  - GET /reports : liste paginée {items, total, page, pages}
  - PATCH /reports/{id} : renommage
  - DELETE /reports/{id}
  - GET /reports/{id}/pdf : PDF valide (magic %PDF)
  - RBAC : 401 sans token
"""
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User, UserRole
from app.agents.report_generator_agent import report_generator_agent
from tests.conftest import VALID_PASSWORD


async def _make_admin_token(client: AsyncClient, db: AsyncSession) -> str:
    admin = User(
        id=uuid.uuid4(),
        email="admin_reports@example.com",
        username="admin_reports",
        hashed_password=hash_password(VALID_PASSWORD),
        full_name="Admin Reports",
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
    )
    db.add(admin)
    await db.commit()
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin_reports@example.com", "password": VALID_PASSWORD},
    )
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


SAMPLE_SUMMARY = {
    "total_jobs": 8, "active_jobs": 3, "total_applications": 40,
    "acceptance_rate": 5.0, "average_score": 45.2,
    "applications_by_status": {"PENDING": 25, "INTERVIEW_SCHEDULED": 3, "NEGOTIATION": 1},
    "top_jobs": [{"title": "DevOps Engineer", "application_count": 18}],
}


# ── Agent de reporting ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_report_agent_structure():
    result = await report_generator_agent.run(SAMPLE_SUMMARY)
    assert set(result) >= {"narrative", "highlights", "recommendations", "generated_by"}
    assert result["generated_by"] in ("deterministic", "claude")
    assert "8 offres" in result["narrative"]
    assert isinstance(result["highlights"], list) and result["highlights"]
    assert isinstance(result["recommendations"], list) and result["recommendations"]


@pytest.mark.asyncio
async def test_report_agent_contextual_insights():
    result = await report_generator_agent.run(SAMPLE_SUMMARY)
    joined = " ".join(result["highlights"] + result["recommendations"])
    # 25/40 en attente (> 50 %) → backlog signalé + recommandation associée.
    assert "attente" in joined
    # Vivier faible (score 45.2) → signalé.
    assert "vivier" in joined.lower()
    # Top job cité.
    assert "DevOps Engineer" in joined


# ── PDF ───────────────────────────────────────────────────────────────────────

def test_pdf_service_renders_valid_pdf():
    from app.services.pdf_service import render_report_pdf
    data = {**SAMPLE_SUMMARY, "report": {
        "narrative": "Synthèse test.", "highlights": ["point"], "recommendations": ["reco"],
    }}
    pdf = render_report_pdf(title="Rapport test", data=data)
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 1500


# ── API bout-en-bout ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reports_require_auth(client: AsyncClient):
    resp = await client.get("/api/v1/reports")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_reports_full_crud_flow(client: AsyncClient, db: AsyncSession):
    token = await _make_admin_token(client, db)

    # 1. Génération (l'agent doit enrichir le snapshot).
    created = await client.post(
        "/api/v1/reports/snapshot", json={"title": "Rapport de test"}, headers=_auth(token)
    )
    assert created.status_code == 201, created.text
    snap = created.json()
    assert snap["title"] == "Rapport de test"
    assert "report" in snap["data"], "le contenu de l'agent doit être inclus"
    assert snap["data"]["report"]["narrative"]
    snap_id = snap["id"]

    # 2. Liste paginée.
    listing = await client.get("/api/v1/reports?page=1&page_size=5", headers=_auth(token))
    assert listing.status_code == 200
    page = listing.json()
    assert set(page) >= {"items", "total", "page", "pages", "page_size"}
    assert page["total"] >= 1
    assert any(item["id"] == snap_id for item in page["items"])

    # 3. Lecture unitaire.
    got = await client.get(f"/api/v1/reports/{snap_id}", headers=_auth(token))
    assert got.status_code == 200

    # 4. Renommage.
    renamed = await client.patch(
        f"/api/v1/reports/{snap_id}", json={"title": "Rapport renommé"}, headers=_auth(token)
    )
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "Rapport renommé"

    # 5. Téléchargement PDF.
    pdf = await client.get(f"/api/v1/reports/{snap_id}/pdf", headers=_auth(token))
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF-")
    assert "attachment" in pdf.headers.get("content-disposition", "")

    # 6. Suppression puis 404.
    dele = await client.delete(f"/api/v1/reports/{snap_id}", headers=_auth(token))
    assert dele.status_code == 204
    gone = await client.get(f"/api/v1/reports/{snap_id}", headers=_auth(token))
    assert gone.status_code == 404


@pytest.mark.asyncio
async def test_reports_pagination_math(client: AsyncClient, db: AsyncSession):
    token = await _make_admin_token(client, db)
    # Créer 3 rapports puis paginer par 2 → 2 pages.
    for i in range(3):
        await client.post("/api/v1/reports/snapshot", json={"title": f"R{i}"}, headers=_auth(token))

    p1 = (await client.get("/api/v1/reports?page=1&page_size=2", headers=_auth(token))).json()
    p2 = (await client.get("/api/v1/reports?page=2&page_size=2", headers=_auth(token))).json()
    assert p1["total"] == 3 and p1["pages"] == 2
    assert len(p1["items"]) == 2 and len(p2["items"]) == 1
    ids = {i["id"] for i in p1["items"]} | {i["id"] for i in p2["items"]}
    assert len(ids) == 3  # pas de doublon entre pages
