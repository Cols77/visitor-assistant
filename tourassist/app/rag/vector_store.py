from __future__ import annotations

from typing import List, Tuple

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

from tourassist.app import config


class VectorStore:
    def __init__(self) -> None:
        self.client = QdrantClient(url=config.settings.qdrant_url)
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        collections = self.client.get_collections().collections
        if any(c.name == config.settings.qdrant_collection for c in collections):
            return
        self.client.create_collection(
            collection_name=config.settings.qdrant_collection,
            vectors_config=VectorParams(size=config.settings.embedding_dims, distance=Distance.COSINE),
        )

    def upsert(self, points: List[Tuple[str, List[float], dict]]) -> None:
        self.client.upsert(
            collection_name=config.settings.qdrant_collection,
            points=[PointStruct(id=pid, vector=vector, payload=payload) for pid, vector, payload in points],
        )

    def query(self, vector: List[float], tenant_id: str, top_k: int) -> list[dict]:
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
