"""
Base class shared by the platform's AI agents.

Each agent encapsulates one autonomous capability (CV analysis, candidate
recommendation, report generation, monitoring). Agents may optionally use the
Claude client for natural-language output but must always provide a
deterministic fallback so the platform works offline.
"""
import logging
from abc import ABC, abstractmethod
from typing import Any

from app.integrations.claude_client import claude_client


class BaseAgent(ABC):
    name: str = "base"

    def __init__(self) -> None:
        self.logger = logging.getLogger(f"agent.{self.name}")
        self.claude = claude_client

    @property
    def llm_enabled(self) -> bool:
        return self.claude.available

    @abstractmethod
    async def run(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the agent's primary task."""
        raise NotImplementedError
