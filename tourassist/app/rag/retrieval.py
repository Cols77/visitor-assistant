from __future__ import annotations

from typing import List

from tourassist.app import config
from tourassist.app.rag.embeddings import embed_texts
from tourassist.app.rag.vector_store import get_qdrant


def retrieve_context(tenant_id: str, query: str) -> List[dict]:
    vector = embed_texts([query])[0]
    qdrant = get_qdrant()
    return qdrant.query(vector, tenant_id, config.settings.top_k)
