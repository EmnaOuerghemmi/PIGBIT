"""
Recommendation agent — turns a candidate score into a hiring recommendation.

Mirrors the logic exposed by the /decision endpoints so it can be reused by
other agents or background jobs.
"""
from app.agents.base_agent import BaseAgent


class RecommendationAgent(BaseAgent):
    name = "recommendation"

    async def run(self, total_score: float) -> dict:
        if total_score >= 80:
            rec, conf = "HIRE", "high"
            rationale = "Score excellent — profil fortement aligné avec le poste."
        elif total_score >= 65:
            rec, conf = "INTERVIEW", "high"
            rationale = "Bon score — recommandé pour un entretien."
        elif total_score >= 50:
            rec, conf = "HOLD", "medium"
            rationale = "Score moyen — à conserver en liste d'attente."
        else:
            rec, conf = "REJECT", "medium"
            rationale = "Score faible — profil peu aligné avec les exigences."
        return {
            "total_score": total_score,
            "recommendation": rec,
            "confidence": conf,
            "rationale": rationale,
        }


recommendation_agent = RecommendationAgent()
