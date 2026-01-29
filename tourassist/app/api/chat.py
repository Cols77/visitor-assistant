from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, status

from tourassist.app.agents.chat import handle_chat
from tourassist.app.models.schemas import ChatRequest, ChatResponse
from tourassist.app.security.auth import enforce_api_key

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(
    payload: ChatRequest,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> ChatResponse:
    if len(payload.user_message.strip()) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty message")
    if len(payload.user_message) > 2000:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Message too long")
    enforce_api_key(payload.tenant_id, x_api_key)
    response, latency_ms, tokens_used, cost, retrieved_doc_ids = handle_chat(
        payload.tenant_id, payload.session_id, payload.user_message
    )
    return ChatResponse(
        response=response,
        latency_ms=latency_ms,
        tokens_used=tokens_used,
        estimated_cost=cost,
        retrieved_doc_ids=retrieved_doc_ids,
    )
