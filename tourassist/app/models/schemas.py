from __future__ import annotations

from pydantic import BaseModel, Field


class TenantCreateRequest(BaseModel):
    tenant_id: str = Field(..., min_length=2, max_length=64)


class TenantCreateResponse(BaseModel):
    tenant_id: str
    api_key: str


class ChatRequest(BaseModel):
    tenant_id: str
    session_id: str
    user_message: str


class ChatResponse(BaseModel):
    response: str
    latency_ms: float
    tokens_used: int
    estimated_cost: float
    retrieved_doc_ids: list[str]


class IngestResponse(BaseModel):
    document_id: str
    status: str
    chunks_indexed: int
