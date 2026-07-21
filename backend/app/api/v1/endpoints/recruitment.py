from typing import Annotated
from uuid import UUID
from pathlib import Path
import logging
from fastapi import APIRouter, Depends, Query, status, UploadFile, File, HTTPException, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_active_user, require_role
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.recruitment import Application, Candidate, JobOffer
from app.schemas.recruitment import (
    JobOfferCreate, JobOfferUpdate, JobOfferResponse, PaginatedJobOffers,
    CandidateCreate, CandidateResponse, ApplicationCreate, ApplicationUpdate, ApplicationResponse,
    MyApplicationResponse,
)
from app.services.recruitment_service import recruitment_service
from app.services.notification_service import notification_service, APPLICATION_STATUS_LABELS
from app.agents.scoring_agent import scoring_agent

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/jobs", response_model=PaginatedJobOffers)
async def list_jobs(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    search: str | None = None,
    sort_by: str | None = None,
):
    total, jobs = await recruitment_service.get_job_offers(db, page, size, is_active=True, search=search, sort_by=sort_by)
    return PaginatedJobOffers(total=total, page=page, size=size, items=jobs)


@router.get("/jobs/{job_id}", response_model=JobOfferResponse)
async def get_job(job_id: UUID, db: Annotated[AsyncSession, Depends(get_db)]):
    job = await recruitment_service.get_job_offer(db, job_id)
    return job


@router.get("/jobs/{job_id}/applications", response_model=list[ApplicationResponse],
            dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.RH_MANAGER))])
async def get_job_applications(job_id: UUID, db: Annotated[AsyncSession, Depends(get_db)]):
    _, apps = await recruitment_service.get_applications(db, job_id)
    return apps


@router.post("/jobs", response_model=JobOfferResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.RH_MANAGER))])
async def create_job(
    body: JobOfferCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    job = await recruitment_service.create_job_offer(db, body, current_user.id)
    await db.commit()
    await db.refresh(job)

    # Indexation sémantique de l'offre (best-effort).
    try:
        from app.services.semantic_service import semantic_service
        await semantic_service.index_job(db, job)
        await db.commit()
    except Exception as embed_exc:  # pragma: no cover - defensive
        logger.warning(f"Semantic indexing failed for job {job.id}: {embed_exc}")

    await notification_service.notify_admins(
        db, actor=current_user, type="JOB_CREATED",
        title="Nouvelle offre publiée",
        message=f"{current_user.full_name or current_user.username} a publié l'offre « {job.title} ».",
        link="/admin/jobs",
    )
    await db.commit()
    return job


@router.patch("/jobs/{job_id}", response_model=JobOfferResponse,
              dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.RH_MANAGER))])
async def update_job(
    job_id: UUID,
    body: JobOfferUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    job = await recruitment_service.update_job_offer(db, job_id, body)
    await db.commit()
    await db.refresh(job)
    # Le contenu de l'offre a changé → réindexer son embedding (best-effort).
    try:
        from app.services.semantic_service import semantic_service
        await semantic_service.index_job(db, job)
        await db.commit()
    except Exception as embed_exc:  # pragma: no cover - defensive
        logger.warning(f"Semantic reindexing failed for job {job_id}: {embed_exc}")
    return job


@router.put("/jobs/{job_id}", response_model=JobOfferResponse,
            dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.RH_MANAGER))])
async def replace_job(
    job_id: UUID,
    body: JobOfferUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Full update of a job offer (cahier des charges PUT /jobs/{id}).
    Shares the service-level update with PATCH; the difference is semantic —
    PUT expects the complete representation.
    """
    job = await recruitment_service.update_job_offer(db, job_id, body)
    await db.commit()
    await db.refresh(job)
    return job


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.RH_MANAGER))])
async def delete_job(job_id: UUID, db: Annotated[AsyncSession, Depends(get_db)]):
    await recruitment_service.delete_job_offer(db, job_id)
    await db.commit()


@router.post("/apply/{job_id}", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
async def apply_to_job(
    job_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    background_tasks: BackgroundTasks,
    cv_file: UploadFile = File(...),
):
    allowed_types = {"application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
    allowed_extensions = {".pdf", ".doc", ".docx"}

    file_ext = Path(cv_file.filename or "").suffix.lower()
    if cv_file.content_type not in allowed_types and file_ext not in allowed_extensions:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF and Word documents are allowed")

    max_size = 5 * 1024 * 1024
    content = await cv_file.read()
    if len(content) > max_size:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File size must not exceed 5MB")

    try:
        uploads_dir = Path("uploads/cvs")
        uploads_dir.mkdir(parents=True, exist_ok=True)

        cv_path = f"uploads/cvs/{current_user.id}_{job_id}{file_ext}"

        with open(cv_path, "wb") as f:
            f.write(content)

        candidate = await recruitment_service.get_or_create_candidate(db, current_user.id, current_user.full_name or "")
        app = await recruitment_service.apply_to_job(db, candidate.id, job_id, cv_path)
        await db.commit()
        await db.refresh(app)

        logger.info(f"Auto-queuing CV analysis for new application {app.id}")
        background_tasks.add_task(scoring_agent.run_analysis_task, app.id)

        return app
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"File upload failed: {str(e)}")


@router.get("/my-applications", response_model=list[MyApplicationResponse])
async def list_my_applications(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Return the authenticated user's own applications, enriched with the
    associated job offer details (title, salary range, skills, etc.) and
    optional scoring data when available. Accessible to any authenticated
    user — designed for the frontoffice "Mes Candidatures" page.
    """
    return await recruitment_service.get_my_applications(db, current_user.id)


@router.get("/applications", response_model=list[ApplicationResponse],
            dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.RH_MANAGER))])
async def list_applications(
    db: Annotated[AsyncSession, Depends(get_db)],
    job_id: UUID | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    total, apps = await recruitment_service.get_applications(db, job_id, page, size)
    return apps


@router.patch("/applications/{app_id}", response_model=ApplicationResponse,
              dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.RH_MANAGER))])
async def update_application(
    app_id: UUID,
    body: ApplicationUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    app = await recruitment_service.update_application_status(db, app_id, body)
    await db.commit()
    await db.refresh(app)

    # Contexte pour les notifications : candidat (destinataire) + offre.
    ctx = (await db.execute(
        select(Candidate, JobOffer)
        .join(JobOffer, JobOffer.id == app.job_offer_id)
        .where(Candidate.id == app.candidate_id)
    )).first()
    if ctx:
        candidate, job = ctx
        status_label = APPLICATION_STATUS_LABELS.get(app.status, app.status)

        await notification_service.notify_user(
            db, recipient_id=candidate.user_id, type="APPLICATION_STATUS_CHANGED",
            title="Mise à jour de votre candidature",
            message=f"Votre candidature pour « {job.title} » est maintenant : {status_label}.",
            link="/frontoffice/applications",
        )
        await notification_service.notify_admins(
            db, actor=current_user, type="APPLICATION_STATUS_CHANGED",
            title="Statut de candidature modifié",
            message=(f"{current_user.full_name or current_user.username} a changé le statut de "
                     f"la candidature de {candidate.full_name} ({job.title}) → {status_label}."),
            link="/admin/applications",
        )
        await db.commit()

    return app


@router.delete("/applications/{app_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_role(UserRole.ADMIN))])
async def delete_application(app_id: UUID, db: Annotated[AsyncSession, Depends(get_db)]):
    """CAND-08 — delete an application + clean up its CV file and derived data (Admin only)."""
    await recruitment_service.delete_application(db, app_id)
    await db.commit()


# ── Saved jobs (frontoffice bookmarks) ──────────────────────────────────────

@router.get("/saved-jobs", response_model=list[JobOfferResponse])
async def list_saved_jobs(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await recruitment_service.get_saved_jobs(db, current_user.id)


@router.post("/saved-jobs/{job_id}", response_model=JobOfferResponse, status_code=status.HTTP_201_CREATED)
async def save_job(
    job_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    job = await recruitment_service.save_job(db, current_user.id, job_id)
    await db.commit()
    return job


@router.delete("/saved-jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unsave_job(
    job_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await recruitment_service.unsave_job(db, current_user.id, job_id)
    await db.commit()


# ── Export ──────────────────────────────────────────────────────────────────

@router.get("/applications/export",
            dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.RH_MANAGER))])
async def export_applications(
    db: Annotated[AsyncSession, Depends(get_db)],
    job_id: UUID | None = None,
):
    """Export applications as CSV (optionally filtered by job offer)."""
    import csv, io
    from sqlalchemy import select as _select
    from app.models.recruitment import Application as _App, Candidate as _Cand, JobOffer as _Job
    from app.models.user import User as _User

    query = (
        _select(_App, _Cand, _User, _Job)
        .join(_Cand, _App.candidate_id == _Cand.id)
        .join(_User, _Cand.user_id == _User.id)
        .join(_Job, _App.job_offer_id == _Job.id)
        .order_by(_App.created_at.desc())
    )
    if job_id:
        query = query.where(_App.job_offer_id == job_id)
    rows = (await db.execute(query)).all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["candidate_name", "email", "job_title", "status", "applied_at", "cv_file"])
    for app, cand, user, job in rows:
        writer.writerow([
            cand.full_name or "",
            user.email,
            job.title,
            app.status,
            app.created_at.isoformat() if app.created_at else "",
            app.cv_file_path,
        ])
    buffer.seek(0)

    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=applications.csv"},
    )


@router.get("/cv-download/{file_path:path}")
async def download_cv(
    file_path: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    from fastapi.responses import FileResponse
    full_path = Path(file_path)
    if not full_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV file not found")
    return FileResponse(full_path, media_type="application/octet-stream", filename=full_path.name)


@router.get("/cv-preview/{file_path:path}")
async def preview_cv(
    file_path: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    from fastapi.responses import FileResponse
    full_path = Path(file_path)
    if not full_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV file not found")

    media_type = "application/pdf"
    if file_path.endswith(".docx"):
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif file_path.endswith(".doc"):
        media_type = "application/msword"

    return FileResponse(full_path, media_type=media_type)
