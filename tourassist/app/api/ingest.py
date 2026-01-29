from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from tourassist.app import config
from tourassist.app.models.schemas import IngestResponse
from tourassist.app.rag.ingestion import ingest_document
from tourassist.app.security.auth import require_api_key

router = APIRouter()


def _validate_file(file: UploadFile, data: bytes) -> None:
    if file.filename is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing filename")
    if not file.filename.lower().endswith((".pdf", ".txt", ".md")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file type")
    size_mb = len(data) / (1024 * 1024)
    if size_mb > config.settings.max_file_size_mb:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large")


@router.post("/ingest", response_model=IngestResponse)
async def ingest_endpoint(
    tenant_id: str = Form(...),
    file: UploadFile = File(...),
    _api_key: str = Depends(require_api_key),
) -> IngestResponse:
    if len(tenant_id.strip()) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid tenant ID")
    raw = await file.read()
    _validate_file(file, raw)
    document_id, chunks, status_value = ingest_document(tenant_id, file.filename, raw)
    return IngestResponse(document_id=document_id, status=status_value, chunks_indexed=chunks)
