"""
Analyzer agent — turns raw CV text into structured data.

Wraps the deterministic NLP extractor and, when Claude is configured, can
produce a short natural-language summary of the candidate.
"""
from app.agents.base_agent import BaseAgent
from app.services.nlp_service import nlp_service


class AnalyzerAgent(BaseAgent):
    name = "analyzer"

    async def run(self, raw_text: str) -> dict:
        """Extract skills/experience/education/keywords from CV text."""
        extraction = nlp_service.extract_all(raw_text or "")
        extraction["summary"] = self._summarize(raw_text, extraction)
        return extraction

    def _summarize(self, raw_text: str, extraction: dict) -> str:
        skills = ", ".join(extraction.get("skills", [])[:8]) or "non détectées"
        years = extraction.get("experience_years")
        deterministic = (
            f"Profil avec {years if years is not None else '?'} an(s) d'expérience. "
            f"Compétences clés : {skills}."
        )
        if not self.llm_enabled or not raw_text:
            return deterministic
        llm = self.claude.complete(
            prompt=f"Résume ce CV en 2 phrases pour un recruteur:\n\n{raw_text[:4000]}",
            system="Tu es un assistant RH concis et factuel.",
            max_tokens=200,
        )
        return llm or deterministic


analyzer_agent = AnalyzerAgent()
