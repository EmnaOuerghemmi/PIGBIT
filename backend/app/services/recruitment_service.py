import os
import logging
from uuid import UUID
from sqlalchemy import select, func, and_, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.recruitment import JobOffer, Candidate, Application, SavedJob
from app.models.scoring import CandidateScore, CVAnalysis
from app.models.interview import InterviewInvitation, InterviewSlot
from app.schemas.recruitment import JobOfferCreate, JobOfferUpdate, ApplicationUpdate

logger = logging.getLogger(__name__)


class RecruitmentService:

    async def create_job_offer(self, db: AsyncSession, data: JobOfferCreate, created_by: UUID) -> JobOffer:
        job = JobOffer(
            title=data.title,
            description=data.description,
            salary_min=data.salary_min,
            salary_max=data.salary_max,
            required_skills=data.required_skills,
            required_experience_years=data.required_experience_years,
            required_education_level=data.required_education_level,
            weight_skills=data.weight_skills,
            weight_experience=data.weight_experience,
            weight_education=data.weight_education,
            created_by=created_by
        )
        db.add(job)
        await db.flush()
        return job

    async def get_job_offers(self, db: AsyncSession, page: int = 1, size: int = 10, is_active: bool = True, search: str = None, sort_by: str = None) -> tuple[int, list[JobOffer]]:
        filters = [JobOffer.is_active == is_active]
        if search:
            filters.append(JobOffer.title.ilike(f"%{search}%") | JobOffer.description.ilike(f"%{search}%"))

        order = JobOffer.created_at.desc()
        if sort_by == 'oldest':
            order = JobOffer.created_at.asc()
        elif sort_by == 'title':
            order = JobOffer.title.asc()

        query = select(JobOffer).where(*filters).order_by(order)
        total = await db.scalar(select(func.count(JobOffer.id)).where(*filters))
        result = await db.execute(query.limit(size).offset((page - 1) * size))
        return total, result.scalars().all()

    async def get_job_offer(self, db: AsyncSession, job_id: UUID) -> JobOffer:
        result = await db.execute(select(JobOffer).where(JobOffer.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job offer not found")
        return job

    async def update_job_offer(self, db: AsyncSession, job_id: UUID, data: JobOfferUpdate) -> JobOffer:
        job = await self.get_job_offer(db, job_id)
        if data.title is not None:
            job.title = data.title
        if data.description is not None:
            job.description = data.description
        if data.salary_min is not None:
            job.salary_min = data.salary_min
        if data.salary_max is not None:
            job.salary_max = data.salary_max
        if data.required_skills is not None:
            job.required_skills = data.required_skills
        if data.required_experience_years is not None:
            job.required_experience_years = data.required_experience_years
        if data.required_education_level is not None:
            job.required_education_level = data.required_education_level
        if data.weight_skills is not None:
            job.weight_skills = data.weight_skills
        if data.weight_experience is not None:
            job.weight_experience = data.weight_experience
        if data.weight_education is not None:
            job.weight_education = data.weight_education
        if data.is_active is not None:
            job.is_active = data.is_active
        await db.flush()
        return job

    async def delete_job_offer(self, db: AsyncSession, job_id: UUID) -> None:
        job = await self.get_job_offer(db, job_id)
        job.is_active = False
        await db.flush()

    async def get_or_create_candidate(self, db: AsyncSession, user_id: UUID, full_name: str, phone: str = None) -> Candidate:
        result = await db.execute(select(Candidate).where(Candidate.user_id == user_id))
        candidate = result.scalar_one_or_none()
        if not candidate:
            candidate = Candidate(user_id=user_id, full_name=full_name, phone=phone)
            db.add(candidate)
            await db.flush()
        return candidate

    async def apply_to_job(self, db: AsyncSession, candidate_id: UUID, job_offer_id: UUID, cv_file_path: str) -> Application:
        result = await db.execute(select(Application).where(
            and_(Application.candidate_id == candidate_id, Application.job_offer_id == job_offer_id)
        ))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already applied")

        app = Application(candidate_id=candidate_id, job_offer_id=job_offer_id, cv_file_path=cv_file_path, status="PENDING")
        db.add(app)
        await db.flush()
        return app

    async def get_applications(self, db: AsyncSession, job_id: UUID = None, page: int = 1, size: int = 20) -> tuple[int, list[Application]]:
        query = select(Application).order_by(Application.created_at.desc())
        if job_id:
            query = query.where(Application.job_offer_id == job_id)

        count_query = select(func.count(Application.id))
        if job_id:
            count_query = count_query.where(Application.job_offer_id == job_id)
        total = await db.scalar(count_query)

        result = await db.execute(query.limit(size).offset((page - 1) * size))
        return total, result.scalars().all()

    async def get_my_applications(self, db: AsyncSession, user_id: UUID) -> list[dict]:
        """
        Return the current user's applications enriched with job offer details
        and optional score data. Returns dicts that map directly to MyApplicationResponse.
        """
        candidate_result = await db.execute(select(Candidate).where(Candidate.user_id == user_id))
        candidate = candidate_result.scalar_one_or_none()
        if not candidate:
            return []

        query = (
            select(Application, JobOffer, CandidateScore)
            .join(JobOffer, Application.job_offer_id == JobOffer.id)
            .outerjoin(CandidateScore, CandidateScore.application_id == Application.id)
            .where(Application.candidate_id == candidate.id)
            .order_by(Application.created_at.desc())
        )
        result = await db.execute(query)

        items: list[dict] = []
        for app, job, score in result.all():
            items.append({
                "id": app.id,
                "job_offer_id": app.job_offer_id,
                "candidate_id": app.candidate_id,
                "cv_file_path": app.cv_file_path,
                "status": app.status,
                "created_at": app.created_at,
                "updated_at": app.updated_at,
                "job_title": job.title,
                "job_description": job.description,
                "job_salary_min": job.salary_min,
                "job_salary_max": job.salary_max,
                "job_required_skills": job.required_skills,
                "job_required_experience_years": job.required_experience_years,
                "job_required_education_level": job.required_education_level,
                "job_is_active": job.is_active,
                "total_score": score.total_score if score else None,
                "skills_score": score.skills_score if score else None,
                "experience_score": score.experience_score if score else None,
                "education_score": score.education_score if score else None,
            })
        return items

    async def update_application_status(self, db: AsyncSession, app_id: UUID, data: ApplicationUpdate) -> Application:
        result = await db.execute(select(Application).where(Application.id == app_id))
        app = result.scalar_one_or_none()
        if not app:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
        app.status = data.status
        await db.flush()
        return app

    async def delete_application(self, db: AsyncSession, app_id: UUID) -> None:
        """
        Delete an application and clean up everything attached to it:
        the CV file on disk, the score, the CV analysis and any interview
        invitation (+ slots). Used by the admin "Supprimer candidature" action
        (CAND-08).
        """
        result = await db.execute(select(Application).where(Application.id == app_id))
        app = result.scalar_one_or_none()
        if not app:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

        cv_path = app.cv_file_path

        # Free interview slots first (FK → invitations), then invitations.
        inv_ids = (
            await db.execute(
                select(InterviewInvitation.id).where(InterviewInvitation.application_id == app_id)
            )
        ).scalars().all()
        if inv_ids:
            await db.execute(delete(InterviewSlot).where(InterviewSlot.invitation_id.in_(inv_ids)))
            await db.execute(delete(InterviewInvitation).where(InterviewInvitation.id.in_(inv_ids)))

        # Remove derived scoring data (FK → applications, no DB cascade).
        await db.execute(delete(CandidateScore).where(CandidateScore.application_id == app_id))
        await db.execute(delete(CVAnalysis).where(CVAnalysis.application_id == app_id))

        await db.execute(delete(Application).where(Application.id == app_id))
        await db.flush()

        # Best-effort filesystem cleanup — never fail the request because of it.
        if cv_path:
            try:
                if os.path.exists(cv_path):
                    os.remove(cv_path)
            except OSError as exc:
                logger.warning(f"Could not delete CV file {cv_path}: {exc}")

    # ── Saved jobs (frontoffice bookmarks) ──────────────────────────────────

    async def get_saved_jobs(self, db: AsyncSession, user_id: UUID) -> list[JobOffer]:
        result = await db.execute(
            select(JobOffer)
            .join(SavedJob, SavedJob.job_offer_id == JobOffer.id)
            .where(SavedJob.user_id == user_id)
            .order_by(SavedJob.created_at.desc())
        )
        return list(result.scalars().all())

    async def save_job(self, db: AsyncSession, user_id: UUID, job_id: UUID) -> JobOffer:
        job = await self.get_job_offer(db, job_id)  # 404 if missing
        existing = await db.execute(
            select(SavedJob).where(
                and_(SavedJob.user_id == user_id, SavedJob.job_offer_id == job_id)
            )
        )
        if existing.scalar_one_or_none() is None:
            db.add(SavedJob(user_id=user_id, job_offer_id=job_id))
            await db.flush()
        return job

    async def unsave_job(self, db: AsyncSession, user_id: UUID, job_id: UUID) -> None:
        await db.execute(
            delete(SavedJob).where(
                and_(SavedJob.user_id == user_id, SavedJob.job_offer_id == job_id)
            )
        )
        await db.flush()


recruitment_service = RecruitmentService()
