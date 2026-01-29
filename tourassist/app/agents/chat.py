from __future__ import annotations

import time
from typing import Tuple

from tourassist.app.agents.llm_client import chat_completion
from tourassist.app.agents.memory import session_memory
from tourassist.app.observability.metrics import metrics_store
from tourassist.app.rag.retrieval import retrieve_context
from tourassist.app.tools.opening_hours import lookup_opening_hours


SYSTEM_PROMPT = (
    "You are TourAssist, a helpful tourist assistant. "
    "Only answer using the provided context. "
    "If the answer is not in the context, say you don't know and suggest next steps."
)


def _should_use_tool(message: str) -> bool:
    lower = message.lower()
    return "opening hours" in lower or "open" in lower


def _extract_place(message: str) -> str:
    words = [w.strip("?.,!") for w in message.lower().split()]
    for candidate in ("spa", "museum", "aquarium"):
        if candidate in words:
            return candidate
    return ""


def handle_chat(
    tenant_id: str, session_id: str, user_message: str
) -> Tuple[str, float, int, float, list[str]]:
    start = time.perf_counter()
    retrieved = retrieve_context(tenant_id, user_message)
    retrieved_doc_ids = [item["document_id"] for item in retrieved if item.get("document_id")]
    context = "\n".join(item["text"] for item in retrieved if item.get("text"))

    if _should_use_tool(user_message):
        place = _extract_place(user_message)
        if place:
            tool_result = lookup_opening_hours(place)
            response_text = tool_result.opening_hours
        else:
            response_text = "Please specify the place name you are asking about."
        latency_ms = (time.perf_counter() - start) * 1000
        metrics_store.record_latency(latency_ms)
        metrics_store.record_tokens(0)
        metrics_store.record_cost(0.0)
        session_memory.append(session_id, "user", user_message)
        session_memory.append(session_id, "assistant", response_text)
        return response_text, latency_ms, 0, 0.0, retrieved_doc_ids

    low_confidence = not retrieved or all(item.get("score", 0) < 0.2 for item in retrieved)
    if low_confidence:
        response_text = (
            "I don't have enough information in the provided documents to answer that. "
            "Please share more details or upload relevant materials."
        )
        latency_ms = (time.perf_counter() - start) * 1000
        metrics_store.record_latency(latency_ms)
        metrics_store.record_tokens(0)
        metrics_store.record_cost(0.0)
        session_memory.append(session_id, "user", user_message)
        session_memory.append(session_id, "assistant", response_text)
        return response_text, latency_ms, 0, 0.0, retrieved_doc_ids

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(session_memory.get(session_id))
    messages.append({"role": "user", "content": f"Context:\n{context}\n\nQuestion: {user_message}"})

    result = chat_completion(messages)
    latency_ms = (time.perf_counter() - start) * 1000
    metrics_store.record_latency(latency_ms)
    metrics_store.record_tokens(result["tokens_used"])
    metrics_store.record_cost(result["estimated_cost"])

    session_memory.append(session_id, "user", user_message)
    session_memory.append(session_id, "assistant", result["content"])

    return result["content"], latency_ms, result["tokens_used"], result["estimated_cost"], retrieved_doc_ids
