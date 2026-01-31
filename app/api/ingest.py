from __future__ import annotations

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile, status

from app import config
from app.models.schemas import IngestBatchResponse, IngestFileResult, IngestResponse
from app.rag.ingestion import ingest_document
from app.security.auth import enforce_api_key

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
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> IngestResponse:
    enforce_api_key(tenant_id, x_api_key)
    if len(tenant_id.strip()) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid tenant ID")
    raw = await file.read()
    _validate_file(file, raw)
    document_id, chunks, status_value = ingest_document(tenant_id, file.filename, raw)
    return IngestResponse(document_id=document_id, status=status_value, chunks_indexed=chunks)


@router.post("/ingest/folder", response_model=IngestBatchResponse)
async def ingest_folder_endpoint(
    tenant_id: str = Form(...),
    files: list[UploadFile] = File(...),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> IngestBatchResponse:
    enforce_api_key(tenant_id, x_api_key)
    if len(tenant_id.strip()) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid tenant ID")
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No files uploaded")

    results: list[IngestFileResult] = []
    total_chunks = 0
    ingested = 0

    for upload in files:
        raw = await upload.read()
        try:
            _validate_file(upload, raw)
        except HTTPException as exc:
            results.append(
                IngestFileResult(
                    filename=upload.filename or "unknown",
                    error=str(exc.detail),
                )
            )
            continue

        document_id, chunks, status_value = ingest_document(tenant_id, upload.filename, raw)
        results.append(
            IngestFileResult(
                filename=upload.filename,
                document_id=document_id,
                status=status_value,
                chunks_indexed=chunks,
            )
        )
        total_chunks += chunks
        ingested += 1

    return IngestBatchResponse(
        files_total=len(files),
        files_ingested=ingested,
        chunks_indexed=total_chunks,
        results=results,
    )
