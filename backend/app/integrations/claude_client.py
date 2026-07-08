"""
Optional Claude (Anthropic) integration.

The platform works fully without an API key — every AI feature has a
deterministic fallback. When ANTHROPIC_API_KEY is configured, this client
enables richer, LLM-generated text (e.g. candidate summaries, rejection
emails). It imports the `anthropic` SDK lazily so the backend never hard-fails
if the package isn't installed.
"""
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class ClaudeClient:
    def __init__(self) -> None:
        self.api_key: str = settings.ANTHROPIC_API_KEY or ""
        self.model: str = settings.ANTHROPIC_MODEL or "claude-sonnet-4-6"
        self._client = None  # lazily created anthropic.Anthropic instance

    @property
    def available(self) -> bool:
        """True only when both an API key and the SDK are present."""
        if not self.api_key:
            return False
        return self._ensure_client() is not None

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        if not self.api_key:
            return None
        try:
            import anthropic  # lazy import — optional dependency
            self._client = anthropic.Anthropic(api_key=self.api_key)
        except Exception as exc:  # pragma: no cover - depends on optional dep
            logger.warning(f"Anthropic SDK unavailable, Claude features disabled: {exc}")
            self._client = None
        return self._client

    def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 600,
    ) -> Optional[str]:
        """
        Return Claude's text completion, or None when the client is not
        available so callers can fall back to deterministic logic.
        """
        client = self._ensure_client()
        if client is None:
            return None
        try:
            kwargs = {
                "model": self.model,
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system:
                kwargs["system"] = system
            resp = client.messages.create(**kwargs)
            parts = [block.text for block in resp.content if getattr(block, "type", None) == "text"]
            return "\n".join(parts).strip() or None
        except Exception as exc:  # pragma: no cover - network/runtime
            logger.error(f"Claude completion failed: {exc}")
            return None


claude_client = ClaudeClient()
