"""
Report generator agent — produit un rapport RH structuré (narrative, points
clés, recommandations) à partir des KPIs de recrutement.

Comme tous les agents PIQBIT : Claude est utilisé si disponible, sinon un
générateur déterministe produit un rapport exploitable hors-ligne.
"""
from app.agents.base_agent import BaseAgent


class ReportGeneratorAgent(BaseAgent):
    name = "report_generator"

    # ── Fallback déterministe ─────────────────────────────────────────────────

    @staticmethod
    def _narrative(summary: dict) -> str:
        return (
            f"Le portefeuille compte {summary.get('total_jobs', 0)} offres "
            f"({summary.get('active_jobs', 0)} actives) pour "
            f"{summary.get('total_applications', 0)} candidatures reçues. "
            f"Le taux d'acceptation s'établit à {summary.get('acceptance_rate', 0)}% "
            f"et le score IA moyen des candidats est de "
            f"{summary.get('average_score') if summary.get('average_score') is not None else 'N/A'}."
        )

    @staticmethod
    def _highlights(summary: dict) -> list[str]:
        points: list[str] = []
        by_status = summary.get("applications_by_status", {}) or {}
        total = summary.get("total_applications", 0) or 0

        pending = by_status.get("PENDING", 0)
        if total and pending / total > 0.5:
            points.append(
                f"{pending} candidatures ({round(pending / total * 100)}%) sont encore en attente de traitement."
            )
        interviews = by_status.get("INTERVIEW_SCHEDULED", 0)
        if interviews:
            points.append(f"{interviews} entretien(s) planifié(s) en cours de pipeline.")
        negotiations = by_status.get("NEGOTIATION", 0)
        if negotiations:
            points.append(f"{negotiations} négociation(s) salariale(s) en cours.")

        top = summary.get("top_jobs") or []
        if top:
            leader = top[0]
            points.append(
                f"L'offre la plus attractive est « {leader.get('title')} » "
                f"avec {leader.get('application_count', 0)} candidatures."
            )
        avg = summary.get("average_score")
        if avg is not None:
            if avg >= 70:
                points.append(f"Le vivier est de bonne qualité (score IA moyen {avg}/100).")
            elif avg < 50:
                points.append(f"Le vivier est faible (score IA moyen {avg}/100) — revoir le sourcing.")
        if not points:
            points.append("Activité de recrutement encore limitée sur la période.")
        return points

    @staticmethod
    def _recommendations(summary: dict) -> list[str]:
        recs: list[str] = []
        by_status = summary.get("applications_by_status", {}) or {}
        total = summary.get("total_applications", 0) or 0

        if total and by_status.get("PENDING", 0) / total > 0.5:
            recs.append("Prioriser le traitement du backlog de candidatures en attente "
                        "(lancer l'analyse IA groupée depuis la page Recrutement).")
        if summary.get("acceptance_rate", 0) < 10 and total >= 10:
            recs.append("Taux d'acceptation faible : réévaluer les critères des offres "
                        "ou élargir les canaux de sourcing.")
        active, jobs = summary.get("active_jobs", 0), summary.get("total_jobs", 0)
        if jobs and active / jobs < 0.5:
            recs.append(f"Seules {active} offres sur {jobs} sont actives : archiver ou republier les offres dormantes.")
        if not recs:
            recs.append("Le pipeline est sain : maintenir le rythme de traitement actuel.")
        return recs

    # ── Point d'entrée ────────────────────────────────────────────────────────

    async def run(self, summary: dict) -> dict:
        """
        Construit le contenu rédigé d'un rapport à partir d'un
        `recruitment_summary`. Retourne un dict sérialisable :
        { narrative, highlights[], recommendations[], generated_by }
        """
        narrative = self._narrative(summary)
        highlights = self._highlights(summary)
        recommendations = self._recommendations(summary)
        generated_by = "deterministic"

        if self.llm_enabled:
            llm = self.claude.complete(
                prompt=(
                    "Rédige la synthèse d'un rapport RH de recrutement (4-5 phrases, "
                    f"français, factuel) à partir de ces KPIs :\n{summary}"
                ),
                system="Tu es un analyste RH senior. Sois factuel, chiffré et synthétique.",
                max_tokens=400,
            )
            if llm:
                narrative = llm
                generated_by = "claude"

        return {
            "narrative": narrative,
            "highlights": highlights,
            "recommendations": recommendations,
            "generated_by": generated_by,
        }


report_generator_agent = ReportGeneratorAgent()
