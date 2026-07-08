from typing import Annotated
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, status, HTTPException, BackgroundTasks
import logging

from app.core.dependencies import get_current_active_user, require_role
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.recruitment import JobOffer, Application, Candidate
from app.models.scoring import CVAnalysis, CandidateScore
from app.schemas.scoring import (
    CVAnalysisResponse,
    CandidateScoreResponse,
    JobRankingResponse,
    CandidateRankingItem,
    AnalysisStartedResponse,
    BulkAnalysisResponse,
)
from app.agents.scoring_agent import scoring_agent
from app.services.scoring_service import scoring_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/applications/{app_id}/analyze",
    response_model=AnalysisStartedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.RH_MANAGER))],
)
async def analyze_application(
    app_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    background_tasks: BackgroundTasks,
):
    """Trigger CV analysis and scoring for a single application (async)."""
    try:
        # Verify application exists
        app_result = await db.execute(
            select(Application).where(Application.id == app_id)
        )
        app = app_result.scalar_one_or_none()
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found",
            )

        logger.info(f"Queuing CV analysis for application {app_id}")
        background_tasks.add_task(scoring_agent.run_analysis_task, app_id)
        return AnalysisStartedResponse(
            message="Analysis started",
            application_id=app_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error starting analysis"
        )


@router.post(
    "/jobs/{job_id}/analyze-all",
    response_model=BulkAnalysisResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.RH_MANAGER))],
)
async def analyze_all_for_job(
    job_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    background_tasks: BackgroundTasks,
):
    """Trigger CV analysis and scoring for all applications of a job (async)."""
    try:
        # Verify job exists and get application count
        job_result = await db.execute(select(JobOffer).where(JobOffer.id == job_id))
        job = job_result.scalar_one_or_none()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job offer not found",
            )

        # Count applications for this job
        app_count_result = await db.execute(
            select(Application).where(Application.job_offer_id == job_id)
        )
        app_count = len(app_count_result.scalars().all())

        logger.info(f"Queuing bulk analysis for job {job_id} with {app_count} applications")
        background_tasks.add_task(scoring_agent.run_bulk_analysis_task, job_id)
        return BulkAnalysisResponse(
            message="Bulk analysis started",
            job_id=job_id,
            count_queued=app_count,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting bulk analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error starting bulk analysis"
        )


@router.get(
    "/applications/{app_id}/analysis",
    response_model=CVAnalysisResponse,
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.RH_MANAGER))],
)
async def get_cv_analysis(
    app_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get extracted CV data for an application (Admin/HR only)."""
    try:
        analysis = await scoring_service.get_analysis_by_application(db, app_id)
        if not analysis:
            logger.warning(f"CV analysis not found for application {app_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="CV analysis not found. Try triggering analysis with POST /analyze",
            )
        logger.info(f"Retrieved CV analysis for application {app_id}")
        return analysis
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving CV analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving CV analysis"
        )


@router.get(
    "/applications/{app_id}/score",
    response_model=CandidateScoreResponse,
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.RH_MANAGER))],
)
async def get_candidate_score(
    app_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get score for a candidate's application (Admin/HR only)."""
    try:
        # Verify application exists first
        app_result = await db.execute(
            select(Application).where(Application.id == app_id)
        )
        if not app_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found",
            )

        score = await scoring_service.get_score_by_application(db, app_id)
        if not score:
            logger.warning(f"Score not found for application {app_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate score not found. Try triggering analysis with POST /analyze",
            )
        logger.info(f"Retrieved score for application {app_id}: {score.total_score}")
        return score
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving candidate score: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving candidate score"
        )


@router.get(
    "/jobs/{job_id}/ranking",
    response_model=JobRankingResponse,
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.RH_MANAGER))],
)
async def get_job_ranking(
    job_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get ranked candidates for a job offer."""
    try:
        # Verify job exists
        job_result = await db.execute(select(JobOffer).where(JobOffer.id == job_id))
        job = job_result.scalar_one_or_none()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job offer not found",
            )

        scores = await scoring_service.get_scores_by_job(db, job_id)

        if not scores:
            logger.info(f"No scores found for job {job_id}. Candidates may not have been analyzed yet.")
            return JobRankingResponse(
                job_offer_id=job_id,
                total_candidates=0,
                ranking=[],
            )

        # Bulk-fetch active invitations for these applications so we can
        # tell the UI which candidates already have a scheduled interview.
        from app.models.interview import InterviewInvitation, InvitationStatus
        app_ids = [s.application_id for s in scores]
        inv_result = await db.execute(
            select(InterviewInvitation).where(
                InterviewInvitation.application_id.in_(app_ids),
                InterviewInvitation.status.in_(
                    [InvitationStatus.PENDING, InvitationStatus.CONFIRMED]
                ),
            )
        )
        inv_by_app: dict = {}
        for inv in inv_result.scalars().all():
            current = inv_by_app.get(inv.application_id)
            # Prefer CONFIRMED over PENDING when both exist
            if current is None or (
                current.status == InvitationStatus.PENDING
                and inv.status == InvitationStatus.CONFIRMED
            ):
                inv_by_app[inv.application_id] = inv

        ranking = []
        for score in scores:
            inv = inv_by_app.get(score.application_id)
            ranking.append(CandidateRankingItem(
                candidate_id=score.candidate_id,
                application_id=score.application_id,
                total_score=score.total_score,
                rank=score.rank,
                skills_score=score.skills_score,
                experience_score=score.experience_score,
                education_score=score.education_score,
                score_details=score.score_details,
                interview_status=(inv.status.value if inv and hasattr(inv.status, 'value') else (str(inv.status) if inv else None)),
                interview_invitation_id=(inv.id if inv else None),
                interview_confirmed_at=(inv.confirmed_at if inv else None),
            ))

        logger.info(f"Retrieved ranking for job {job_id}: {len(scores)} candidates")
        return JobRankingResponse(
            job_offer_id=job_id,
            total_candidates=len(scores),
            ranking=ranking,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving job ranking: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving job ranking"
        )
