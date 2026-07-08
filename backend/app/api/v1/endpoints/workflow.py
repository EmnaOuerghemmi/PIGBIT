from datetime import datetime
from uuid import UUID
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.core.dependencies import require_role, get_current_active_user
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.recruitment import Application, Candidate, JobOffer
from app.services.email_service import (
    send_interview_invitation_link,
    send_rejection_email,
)
from app.services.interview_service import interview_service, public_url_for
from app.services.notification_service import notification_service

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────────────────────

class ScheduleInterviewRequest(BaseModel):
    """
    The frontend sends a list of ISO-8601 datetimes (one per proposed slot).
    Older clients that send plain strings ('2026-05-20 à 10h00') are still
    handled: we'll try to parse them as ISO first, then fall back to passing
    them straight to the email template.
    """
    slots: list[datetime] = Field(
        ..., min_length=1, max_length=5,
        description="ISO-8601 datetimes — one per proposed slot.",
    )
    duration_minutes: int = Field(default=30, ge=10, le=240)
    expires_in_hours: int = Field(default=48, ge=1, le=336)
    message: str = Field(default="", max_length=2000)


class RejectRequest(BaseModel):
    message: str = Field(default="", max_length=1000)


class StartNegotiationRequest(BaseModel):
    employer_offer: float = Field(..., gt=0, description="Offre salariale initiale (TND)")


class WorkflowResponse(BaseModel):
    message: str
    application_id: UUID
    email_sent: bool = False


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _get_application_context(db: AsyncSession, application_id: UUID):
    """Return (application, candidate, user, job_offer) or raise 404."""
    result = await db.execute(
        select(Application, Candidate, User, JobOffer)
        .join(Candidate, Application.candidate_id == Candidate.id)
        .join(User, Candidate.user_id == User.id)
        .join(JobOffer, Application.job_offer_id == JobOffer.id)
        .where(Application.id == application_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return row  # (application, candidate, user, job_offer)


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post(
    "/applications/{app_id}/schedule-interview",
    response_model=WorkflowResponse,
)
async def schedule_interview(
    app_id: UUID,
    body: ScheduleInterviewRequest,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create an interview invitation with proposed slots and send the candidate
    a public link to choose one. Replaces the old free-text email flow.
    """
    if current_user.role not in (UserRole.ADMIN, UserRole.RH_MANAGER, UserRole.RH_STAFF):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    app, candidate, user, job = await _get_application_context(db, app_id)

    invitation = await interview_service.create_invitation(
        db,
        application_id=app_id,
        slots=body.slots,
        duration_minutes=body.duration_minutes,
        message=body.message,
        expires_in_hours=body.expires_in_hours,
        created_by=current_user.id,
    )

    app.status = "INTERVIEW_SCHEDULED"
    await db.commit()

    background_tasks.add_task(
        send_interview_invitation_link,
        to_email=user.email,
        candidate_name=candidate.full_name,
        job_title=job.title,
        slots=body.slots,
        public_url=public_url_for(invitation.token),
        message=body.message,
        expires_at=invitation.expires_at,
    )

    logger.info(f"Interview invitation {invitation.id} created for application {app_id}, "
                f"email queued to {user.email}, public_url={public_url_for(invitation.token)}")

    await notification_service.notify_user(
        db, recipient_id=user.id, type="INTERVIEW_SCHEDULED",
        title="Entretien proposé",
        message=f"Un entretien vous a été proposé pour « {job.title} ». Choisissez votre créneau.",
        link="/frontoffice/applications",
    )
    await notification_service.notify_admins(
        db, actor=current_user, type="INTERVIEW_SCHEDULED",
        title="Entretien planifié",
        message=(f"{current_user.full_name or current_user.username} a planifié un entretien "
                 f"pour {candidate.full_name} ({job.title})."),
        link="/admin/interviews",
    )
    await db.commit()

    return WorkflowResponse(
        message="Invitation d'entretien envoyée. Le candidat va recevoir un lien pour choisir son créneau.",
        application_id=app_id,
        email_sent=True,
    )


@router.post(
    "/applications/{app_id}/reject",
    response_model=WorkflowResponse,
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.RH_MANAGER, UserRole.RH_STAFF))],
)
async def reject_application(
    app_id: UUID,
    body: RejectRequest,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Reject the application and send a rejection email to the candidate."""
    app, candidate, user, job = await _get_application_context(db, app_id)

    app.status = "REJECTED"
    await db.commit()

    background_tasks.add_task(
        send_rejection_email,
        user.email,
        candidate.full_name,
        job.title,
        body.message,
    )

    await notification_service.notify_user(
        db, recipient_id=user.id, type="APPLICATION_STATUS_CHANGED",
        title="Candidature rejetée",
        message=f"Votre candidature pour « {job.title} » n'a pas été retenue.",
        link="/frontoffice/applications",
    )
    await notification_service.notify_admins(
        db, actor=current_user, type="APPLICATION_STATUS_CHANGED",
        title="Candidature rejetée",
        message=(f"{current_user.full_name or current_user.username} a rejeté la candidature "
                 f"de {candidate.full_name} ({job.title})."),
        link="/admin/applications",
    )
    await db.commit()

    logger.info(f"Application {app_id} rejected, email queued to {user.email}")
    return WorkflowResponse(
        message="Candidature rejetée. Email de refus envoyé.",
        application_id=app_id,
        email_sent=True,
    )


@router.post(
    "/applications/{app_id}/start-negotiation",
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.RH_MANAGER))],
)
async def start_negotiation(
    app_id: UUID,
    body: StartNegotiationRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Mark the application as NEGOTIATION and RUN the salary-negotiation agent
    end-to-end (salary prediction + offer evaluation + simulated counter-offers),
    returning the full outcome so the RH sees the result immediately.
    """
    app, candidate, user, job = await _get_application_context(db, app_id)

    app.status = "NEGOTIATION"
    await db.commit()

    await notification_service.notify_user(
        db, recipient_id=user.id, type="NEGOTIATION_STARTED",
        title="Négociation salariale lancée",
        message=f"Une négociation salariale a démarré pour « {job.title} ».",
        link="/frontoffice/applications",
    )
    await notification_service.notify_admins(
        db, actor=current_user, type="NEGOTIATION_STARTED",
        title="Négociation salariale lancée",
        message=(f"{current_user.full_name or current_user.username} a lancé une négociation "
                 f"pour {candidate.full_name} ({job.title})."),
        link="/admin/negotiation",
    )
    await db.commit()

    # Derive the feature flags the salary model/heuristic expects from the job.
    skills_blob = " ".join(s.lower() for s in (job.required_skills or []))
    job_data = {
        "job_id": str(app_id),
        "title": job.title,
        "description": job.description or "",
        "rating": 3.5,
        "experience_years": job.required_experience_years,
        "skills_text": skills_blob,
        "python": 1 if "python" in skills_blob else 0,
        "spark": 1 if "spark" in skills_blob else 0,
        "aws": 1 if "aws" in skills_blob else 0,
        "excel": 1 if "excel" in skills_blob else 0,
    }

    try:
        from app.services.salary_prediction_service import get_salary_service
        from app.agents.decision_agent import get_negotiation_agent

        prediction = get_salary_service().predict_salary(job_data)
        agent = get_negotiation_agent()
        result = await agent.initiate_negotiation(
            job_id=str(app_id),
            candidate_id=str(candidate.id),
            job_data=job_data,
            employer_offer=body.employer_offer,
        )
        logger.info(f"Negotiation executed for application {app_id}: "
                    f"{result.get('negotiation_status')} @ {result.get('final_salary')}k")

        # Persister la négociation issue du workflow RH (best-effort).
        try:
            from app.services.negotiation_repository import negotiation_repository
            await negotiation_repository.persist_agent_run(
                db, candidate_id=str(candidate.id), result=result, job_offer_id=job.id
            )
            await db.commit()
        except Exception as persist_exc:  # pragma: no cover - defensive
            logger.warning(f"Persistance de la négociation (workflow) échouée: {persist_exc}")
        return {
            "message": "Négociation exécutée par l'agent IA.",
            "application_id": str(app_id),
            "candidate_name": candidate.full_name,
            "employer_offer": body.employer_offer,
            "predicted_salary": prediction.get("predicted_salary"),
            "confidence": prediction.get("confidence"),
            "predicted_range": [prediction.get("range_min"), prediction.get("range_max")],
            "model_type": prediction.get("model_type"),
            "negotiation_status": result.get("negotiation_status"),
            "final_salary": result.get("final_salary"),
            "rounds": result.get("negotiation_rounds"),
            "reason": result.get("reason"),
            "summary": result.get("summary"),
        }
    except Exception as exc:  # pragma: no cover - keep the status change even if the agent fails
        logger.error(f"Negotiation agent failed for application {app_id}: {exc}", exc_info=True)
        return {
            "message": "Statut mis à jour en « Négociation » (moteur indisponible).",
            "application_id": str(app_id),
            "employer_offer": body.employer_offer,
            "error": str(exc),
        }
