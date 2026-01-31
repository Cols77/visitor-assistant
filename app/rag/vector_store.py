from __future__ import annotations

from typing import List, Tuple

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

from app import config
from app.models.db import get_connection
from app.observability.logger import get_logger
from app.rag.embeddings import embed_texts


class VectorStore:
    def __init__(self) -> None:
        self.client = QdrantClient(url=config.settings.qdrant_url)
        self.logger = get_logger(__name__)
        self._reindexing = False

    def _existing_collection_size(self) -> int | None:
        collections = self.client.get_collections().collections
        if not any(c.name == config.settings.qdrant_collection for c in collections):
            return None
        info = self.client.get_collection(collection_name=config.settings.qdrant_collection)
        vectors = info.config.params.vectors
        if isinstance(vectors, dict):
            first = next(iter(vectors.values()))
            return first.size
        return vectors.size

    def _ensure_collection(self, vector_size: int) -> None:
        existing_size = self._existing_collection_size()
        if existing_size is None:
            self.client.create_collection(
                collection_name=config.settings.qdrant_collection,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
            return
        if existing_size != vector_size:
            self._rebuild_collection(existing_size, vector_size)

    def _rebuild_collection(self, existing_size: int, vector_size: int) -> None:
        if self._reindexing:
            raise ValueError(
                "Qdrant collection vector size mismatch while rebuilding: "
                f"{existing_size} existing vs {vector_size} requested."
            )
        self._reindexing = True
        try:
            self.logger.warning(
                "qdrant_collection_mismatch_reindex",
                extra={"extra": {"existing_size": existing_size, "requested_size": vector_size}},
            )
            self.client.delete_collection(collection_name=config.settings.qdrant_collection)
            self.client.create_collection(
                collection_name=config.settings.qdrant_collection,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
            self._reindex_from_db()
        finally:
            self._reindexing = False

    def _reindex_from_db(self) -> None:
        conn = get_connection()
        rows = conn.execute(
            """
            SELECT
                chunks.qdrant_id,
                chunks.text,
                chunks.tenant_id,
                chunks.document_id,
                chunks.chunk_index,
                documents.filename
            FROM chunks
            JOIN documents ON documents.document_id = chunks.document_id
            ORDER BY chunks.document_id, chunks.chunk_index
            """
        ).fetchall()
        conn.close()
        if not rows:
            self.logger.info("qdrant_reindex_empty")
            return

        batch_size = 64
        for start in range(0, len(rows), batch_size):
            batch = rows[start : start + batch_size]
            texts = [row["text"] for row in batch]
            vectors = embed_texts(texts)
            points = []
            for row, vector in zip(batch, vectors):
                points.append(
                    PointStruct(
                        id=row["qdrant_id"],
                        vector=vector,
                        payload={
                            "tenant_id": row["tenant_id"],
                            "document_id": row["document_id"],
                            "chunk_index": row["chunk_index"],
                            "text": row["text"],
                            "source": row["filename"],
                        },
                    )
                )
            self.client.upsert(
                collection_name=config.settings.qdrant_collection,
                points=points,
            )

    def upsert(self, points: List[Tuple[str, List[float], dict]]) -> None:
        if points:
            self._ensure_collection(len(points[0][1]))
        self.client.upsert(
            collection_name=config.settings.qdrant_collection,
            points=[PointStruct(id=pid, vector=vector, payload=payload) for pid, vector, payload in points],
        )

    def query(self, vector: List[float], tenant_id: str, top_k: int) -> list[dict]:
        self._ensure_collection(len(vector))
        results = self.client.search(
            collection_name=config.settings.qdrant_collection,
            query_vector=vector,
            limit=top_k,
            query_filter=Filter(
                must=[FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))]
            ),
        )
        return [
            {
                "document_id": hit.payload.get("document_id"),
                "text": hit.payload.get("text"),
                "source": hit.payload.get("source"),
                "score": hit.score,
            }
            for hit in results
        ]


_vector_store: VectorStore | None = None


def get_qdrant() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
