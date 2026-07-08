"""
Persistence layer for salary negotiations.

The negotiation *engine* (DecisionService / NegotiationAgent) stays in charge of
the decision logic; this repository is the thin async data-access layer that
stores each negotiation and its rounds in PostgreSQL so they survive a restart
and can be audited / listed by RH.
"""
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.negotiation import Negotiation, NegotiationRound


class NegotiationRepository:
    """Async CRUD helpers for `negotiations` / `negotiation_rounds`."""

    async def create(
        self,
        db: AsyncSession,
        *,
        job_id: str,
        candidate_id: str,
        initial_offer: float,
        predicted_salary: Optional[float] = None,
        confidence: Optional[float] = None,
        max_iterations: int = 5,
        job_offer_id=None,
    ) -> Negotiation:
        negotiation = Negotiation(
            job_id=str(job_id),
            candidate_id=str(candidate_id),
            initial_offer=float(initial_offer),
            predicted_salary=predicted_salary,
            confidence=confidence,
            max_iterations=max_iterations,
            job_offer_id=job_offer_id,
            status="ONGOING",
        )
        db.add(negotiation)
        await db.flush()
        # Load server-side defaults (created_at/updated_at) so callers can build
        # a summary from the returned object without triggering a lazy refresh.
        await db.refresh(negotiation)
        return negotiation

    async def add_round(
        self,
        db: AsyncSession,
        negotiation: Negotiation,
        *,
        actor: str,
        amount: Optional[float] = None,
        decision: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> NegotiationRound:
        """Append a round and keep `rounds_count` in sync."""
        negotiation.rounds_count = (negotiation.rounds_count or 0) + 1
        rnd = NegotiationRound(
            negotiation_id=negotiation.id,
            round_number=negotiation.rounds_count,
            actor=actor,
            amount=amount,
            decision=decision,
            reason=reason,
        )
        db.add(rnd)
        await db.flush()
        # Updating rounds_count fires the negotiation's server-side `onupdate`,
        # which expires updated_at; refresh so the object stays fully loaded.
        await db.refresh(negotiation)
        await db.refresh(rnd)
        return rnd

    async def finalize(
        self,
        db: AsyncSession,
        negotiation: Negotiation,
        *,
        status: str,
        final_salary: Optional[float],
        reason: Optional[str] = None,
    ) -> Negotiation:
        negotiation.status = status
        negotiation.final_salary = final_salary
        negotiation.reason = reason
        await db.flush()
        await db.refresh(negotiation)
        return negotiation

    async def get_latest_by_job(self, db: AsyncSession, job_id: str) -> Optional[Negotiation]:
        """Most recent negotiation for a given business job id."""
        result = await db.execute(
            select(Negotiation)
            .where(Negotiation.job_id == str(job_id))
            .order_by(Negotiation.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, db: AsyncSession, negotiation_id) -> Optional[Negotiation]:
        result = await db.execute(select(Negotiation).where(Negotiation.id == negotiation_id))
        return result.scalar_one_or_none()

    async def list_rounds(self, db: AsyncSession, negotiation_id) -> list[NegotiationRound]:
        result = await db.execute(
            select(NegotiationRound)
            .where(NegotiationRound.negotiation_id == negotiation_id)
            .order_by(NegotiationRound.round_number)
        )
        return list(result.scalars().all())

    async def list(
        self,
        db: AsyncSession,
        *,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Negotiation]:
        query = (
            select(Negotiation)
            .options(selectinload(Negotiation.rounds))
            .order_by(Negotiation.created_at.desc())
        )
        if status:
            query = query.where(Negotiation.status == status)
        query = query.limit(limit).offset(offset)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def stats(self, db: AsyncSession) -> dict:
        rows = (
            await db.execute(
                select(Negotiation.status, func.count(Negotiation.id)).group_by(Negotiation.status)
            )
        ).all()
        counts = {s: c for s, c in rows}
        return {
            "ongoing": counts.get("ONGOING", 0),
            "accepted": counts.get("ACCEPTED", 0),
            "rejected": counts.get("REJECTED", 0),
            "compromis": counts.get("COMPROMIS", 0),
            "pending": counts.get("PENDING", 0),
            "total": sum(counts.values()),
        }

    async def persist_agent_run(
        self,
        db: AsyncSession,
        *,
        candidate_id: str,
        result: dict,
        job_offer_id=None,
    ) -> Optional[Negotiation]:
        """
        Miroir en base d'un run in-memory de l'agent de négociation.

        Lit le contexte laissé par l'agent (offre initiale, contre-offres) et
        écrit une ligne `negotiations` + ses `negotiation_rounds`. Best-effort :
        appelée sous try/except par les endpoints, ne doit jamais casser la
        réponse live. Retourne la négociation créée (ou None si pas de contexte).
        """
        # Import tardif : évite de charger la stack ML (agent) au démarrage.
        from app.agents.decision_agent import get_negotiation_agent

        job_id = result.get("job_id")
        if not job_id:
            return None
        context = get_negotiation_agent().decision_service.get_negotiation(job_id)
        if context is None:
            return None

        negotiation = await self.create(
            db,
            job_id=job_id,
            candidate_id=candidate_id,
            initial_offer=context.initial_offer,
            predicted_salary=result.get("predicted_salary"),
            confidence=result.get("confidence"),
            max_iterations=context.max_iterations,
            job_offer_id=job_offer_id,
        )

        # Round 0 : offre initiale de l'employeur.
        await self.add_round(
            db, negotiation, actor="employer", amount=context.initial_offer,
            decision="pending", reason="Offre initiale de l'employeur",
        )
        # Contre-offres produites par le moteur.
        for co in context.counter_offers:
            await self.add_round(
                db, negotiation, actor="candidate", amount=co.get("amount"),
                decision="counter_offer", reason=co.get("reason"),
            )

        status_map = {"ACCEPTED": "ACCEPTED", "REJECTED": "REJECTED", "COMPROMIS": "COMPROMIS"}
        final_status = status_map.get(result.get("negotiation_status"), "ONGOING")
        await self.finalize(
            db, negotiation,
            status=final_status,
            final_salary=result.get("final_salary"),
            reason=result.get("reason"),
        )
        return negotiation

    @staticmethod
    def to_summary(negotiation: Negotiation, rounds: Optional[list[NegotiationRound]] = None) -> dict:
        """Serialise a negotiation (+ its rounds) into a JSON-friendly dict."""
        rounds = rounds if rounds is not None else list(negotiation.rounds)
        return {
            "id": str(negotiation.id),
            "job_id": negotiation.job_id,
            "candidate_id": negotiation.candidate_id,
            "predicted_salary": negotiation.predicted_salary,
            "confidence": negotiation.confidence,
            "initial_offer": negotiation.initial_offer,
            "final_salary": negotiation.final_salary,
            "status": negotiation.status,
            "reason": negotiation.reason,
            "rounds_count": negotiation.rounds_count,
            "max_iterations": negotiation.max_iterations,
            "created_at": negotiation.created_at.isoformat() if negotiation.created_at else None,
            "updated_at": negotiation.updated_at.isoformat() if negotiation.updated_at else None,
            "rounds": [
                {
                    "round_number": r.round_number,
                    "actor": r.actor,
                    "amount": r.amount,
                    "decision": r.decision,
                    "reason": r.reason,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rounds
            ],
        }


negotiation_repository = NegotiationRepository()
