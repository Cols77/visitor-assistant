from __future__ import annotations

import json
from typing import Any

import httpx

from tourassist.app import config
from tourassist.app.observability.logger import get_logger

logger = get_logger(__name__)


def _estimate_tokens(text: str) -> int:
    return max(1, int(len(text.split()) * 1.3))


def _estimate_cost(tokens: int) -> float:
    return round(tokens * 0.0000005, 6)


def chat_completion(messages: list[dict[str, str]]) -> dict[str, Any]:
    if not config.settings.llm_api_key:
        content = "\n".join(m["content"] for m in messages if m["role"] != "system")
        response = {
            "content": f"Based on the provided documents, here is what I found:\n{content}",
            "tokens_used": _estimate_tokens(content),
            "estimated_cost": _estimate_cost(_estimate_tokens(content)),
        }
        return response

    payload = {"model": config.settings.llm_model, "messages": messages}
    headers = {"Authorization": f"Bearer {config.settings.llm_api_key}"}
    try:
        with httpx.Client(timeout=20) as client:
            response = client.post(
                f"{config.settings.llm_base_url}/chat/completions", json=payload, headers=headers
            )
            response.raise_for_status()
            data = response.json()
        choice = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        tokens = usage.get("total_tokens", _estimate_tokens(choice))
        return {"content": choice, "tokens_used": tokens, "estimated_cost": _estimate_cost(tokens)}
    except Exception as exc:  # noqa: BLE001
        logger.error("chat_completion_failed", extra={"extra": {"error": str(exc)}})
        fallback = "I'm sorry, I'm having trouble right now. Please try again shortly."
        tokens = _estimate_tokens(fallback)
        return {"content": fallback, "tokens_used": tokens, "estimated_cost": _estimate_cost(tokens)}
