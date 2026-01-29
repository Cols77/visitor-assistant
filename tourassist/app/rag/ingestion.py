from __future__ import annotations

import hashlib
import io
import uuid
from datetime import datetime, timezone
from typing import Iterable, Tuple

from pypdf import PdfReader

from tourassist.app import config
from tourassist.app.models.db import get_connection
from tourassist.app.observability.logger import get_logger
from tourassist.app.rag.embeddings import embed_texts
from tourassist.app.rag.vector_store import get_qdrant

logger = get_logger(__name__)


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_pdf(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _read_text(data: bytes) -> str:
    return data.decode("utf-8", errors="ignore")


def extract_text(filename: str, data: bytes) -> str:
    if filename.lower().endswith(".pdf"):
        return _read_pdf(data)
    return _read_text(data)


def chunk_text(text: str, max_chars: int) -> Iterable[str]:
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks = []
    current = []
    size = 0
    for paragraph in paragraphs:
        if size + len(paragraph) + 1 > max_chars and current:
            chunks.append(" ".join(current))
            current = [paragraph]
            size = len(paragraph)
        else:
            current.append(paragraph)
            size += len(paragraph) + 1
    if current:
        chunks.append(" ".join(current))
    return chunks


def ingest_document(tenant_id: str, filename: str, data: bytes) -> Tuple[str, int, str]:
    content_hash = _hash_bytes(data)
    conn = get_connection()
    existing = conn.execute(
        "SELECT document_id, status FROM documents WHERE tenant_id = ? AND content_hash = ?",
        (tenant_id, content_hash),
    ).fetchone()
    if existing:
        conn.close()
        return existing["document_id"], 0, existing["status"]

    document_id = str(uuid.uuid4())
    with conn:
        conn.execute(
            "INSERT INTO documents (document_id, tenant_id, filename, content_hash, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                document_id,
                tenant_id,
                filename,
                content_hash,
                "processing",
                datetime.now(timezone.utc).isoformat(),
            ),
        )
    conn.close()

    text = extract_text(filename, data)
    chunks = list(chunk_text(text, config.settings.max_chunk_chars))
    vectors = embed_texts(chunks)
    qdrant = get_qdrant()
    points = []
    chunk_rows = []
    for idx, (chunk, vector) in enumerate(zip(chunks, vectors)):
        qdrant_id = str(uuid.uuid4())
        points.append(
            (
                qdrant_id,
                vector,
                {
                    "tenant_id": tenant_id,
                    "document_id": document_id,
                    "chunk_index": idx,
                    "text": chunk,
                    "source": filename,
                },
            )
        )
        chunk_rows.append((str(uuid.uuid4()), tenant_id, document_id, idx, chunk, qdrant_id))

    if points:
        qdrant.upsert(points)

    conn = get_connection()
    with conn:
        conn.executemany(
            "INSERT INTO chunks (chunk_id, tenant_id, document_id, chunk_index, text, qdrant_id) VALUES (?, ?, ?, ?, ?, ?)",
            chunk_rows,
        )
        conn.execute(
            "UPDATE documents SET status = ? WHERE document_id = ?",
            ("ready", document_id),
        )
    conn.close()

    logger.info("ingest_complete", extra={"extra": {"tenant_id": tenant_id, "document_id": document_id}})
    return document_id, len(chunks), "ready"
