from uuid import UUID
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
import logging

from app.db.session import AsyncSessionLocal
from app.models.recruitment import JobOffer, Application
from app.models.scoring import CVAnalysis, CandidateScore
from app.services.cv_parser import cv_parser
from app.services.nlp_service import nlp_service
from app.services.scoring_service import scoring_service

logger = logging.getLogger(__name__)


class ScoringAgent:
    async def analyze_application(
        self, db: AsyncSession, application_id: UUID
    ) -> CandidateScore:
        """
        Analyze a single application:
        1. Load Application + JobOffer
        2. Extract text from CV
        3. Run NLP extraction
        4. Compute scores
        5. Update ranks for the job
        """
        result = await db.execute(
            select(Application).where(Application.id == application_id)
        )
        application = result.scalar_one_or_none()
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found",
            )

        result = await db.execute(
            select(JobOffer).where(JobOffer.id == application.job_offer_id)
        )
        job_offer = result.scalar_one_or_none()
        if not job_offer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job offer not found",
            )

        logger.info(f"Analyzing application {application_id} for job {job_offer.id}")

        raw_text = await cv_parser.extract_text(application.cv_file_path)
        if not raw_text:
            logger.warning(f"Could not extract text from CV: {application.cv_file_path}")

        extraction = nlp_service.extract_all(raw_text)

        result = await db.execute(
            select(CVAnalysis).where(CVAnalysis.application_id == application_id)
        )
        existing_analysis = result.scalar_one_or_none()

        if existing_analysis:
            existing_analysis.raw_text = raw_text
            existing_analysis.extracted_skills = extraction["skills"]
            existing_analysis.extracted_experience_years = extraction["experience_years"]
            existing_analysis.extracted_education_level = extraction["education_level"]
            existing_analysis.extracted_job_titles = extraction["job_titles"]
            existing_analysis.extracted_keywords = extraction["keywords"]
            existing_analysis.is_parsed = True
            existing_analysis.parsed_at = datetime.utcnow()
            analysis = existing_analysis
        else:
            analysis = CVAnalysis(
                application_id=application_id,
                candidate_id=application.candidate_id,
                raw_text=raw_text,
                extracted_skills=extraction["skills"],
                extracted_experience_years=extraction["experience_years"],
                extracted_education_level=extraction["education_level"],
                extracted_job_titles=extraction["job_titles"],
                extracted_keywords=extraction["keywords"],
                is_parsed=True,
                parsed_at=datetime.utcnow(),
            )
            db.add(analysis)

        await db.flush()

        # Indexation sémantique du CV (embeddings) — best-effort.
        try:
            from app.services.semantic_service import semantic_service
            await semantic_service.index_cv(db, analysis)
        except Exception as embed_exc:  # pragma: no cover - defensive
            logger.warning(f"Semantic indexing failed for application {application_id}: {embed_exc}")

        score = await scoring_service.compute_and_store_score(
            db,
            application_id,
            job_offer.id,
            application.candidate_id,
            analysis,
            job_offer,
        )

        await scoring_service.rank_candidates_for_job(db, job_offer.id)

        logger.info(
            f"Computed score for application {application_id}: {score.total_score}"
        )
        return score

    async def analyze_all_for_job(
        self, db: AsyncSession, job_offer_id: UUID
    ) -> int:
        """
        Analyze all applications for a job offer.
        Returns count of applications analyzed.
        """
        result = await db.execute(
            select(JobOffer).where(JobOffer.id == job_offer_id)
        )
        job_offer = result.scalar_one_or_none()
        if not job_offer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job offer not found",
            )

        result = await db.execute(
            select(Application).where(
                Application.job_offer_id == job_offer_id
            )
        )
        applications = result.scalars().all()

        logger.info(
            f"Analyzing {len(applications)} applications for job {job_offer_id}"
        )

        for app in applications:
            try:
                await self.analyze_application(db, app.id)
            except Exception as e:
                logger.error(f"Error analyzing application {app.id}: {str(e)}")
                continue

        return len(applications)

    async def run_analysis_task(self, application_id: UUID) -> None:
        """
        Background task wrapper. Opens its own DB session so it stays valid
        after the originating HTTP request closes its session.
        """
        async with AsyncSessionLocal() as db:
            try:
                await self.analyze_application(db, application_id)
                await db.commit()
                logger.info(f"Background analysis committed for application {application_id}")
            except Exception as e:
                await db.rollback()
                logger.error(
                    f"Background analysis failed for application {application_id}: {str(e)}",
                    exc_info=True,
                )

    async def run_bulk_analysis_task(self, job_offer_id: UUID) -> None:
        """
        Background task wrapper for bulk analysis. Opens its own DB session.
        """
        async with AsyncSessionLocal() as db:
            try:
                count = await self.analyze_all_for_job(db, job_offer_id)
                await db.commit()
                logger.info(
                    f"Background bulk analysis committed for job {job_offer_id}: {count} applications"
                )
            except Exception as e:
                await db.rollback()
                logger.error(
                    f"Background bulk analysis failed for job {job_offer_id}: {str(e)}",
                    exc_info=True,
                )


scoring_agent = ScoringAgent()
