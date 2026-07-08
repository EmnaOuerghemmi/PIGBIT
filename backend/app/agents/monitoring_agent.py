"""
Monitoring agent — lightweight health/usage probe for the AI subsystem.

Reports which AI capabilities are currently available so the rest of the app
(and ops dashboards) can degrade gracefully.
"""
from datetime import datetime, timezone

from app.agents.base_agent import BaseAgent
from app.services.salary_prediction_service import get_salary_service


class MonitoringAgent(BaseAgent):
    name = "monitoring"

    async def run(self) -> dict:
        try:
            salary = get_salary_service()
            salary_mode = "heuristic" if getattr(salary, "heuristic", False) else "ml_model"
        except Exception:
            salary_mode = "unavailable"
        return {
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "llm_enabled": self.llm_enabled,
            "salary_prediction_mode": salary_mode,
            "status": "ok",
        }


monitoring_agent = MonitoringAgent()
