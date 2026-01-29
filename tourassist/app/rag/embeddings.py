from __future__ import annotations

import hashlib
import json
from typing import Iterable, List

import httpx

from tourassist.app import config
from tourassist.app.models.db import get_connection
from tourassist.app.observability.logger import get_logger

logger = get_logger(__name__)


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _cached_embedding(text_hash: str) -> List[float] | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT vector_json FROM embeddings_cache WHERE text_hash = ?",
        (text_hash,),
    ).fetchone()
    conn.close()
    if not row:
        return None
    return json.loads(row["vector_json"])


def _store_embedding(text_hash: str, vector: List[float]) -> None:
    conn = get_connection()
    with conn:
        conn.execute(
            "INSERT OR REPLACE INTO embeddings_cache (text_hash, vector_json) VALUES (?, ?)",
            (text_hash, json.dumps(vector)),
        )
    conn.close()


def _deterministic_embedding(text: str, dims: int) -> List[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values = [b / 255 for b in digest]
    while len(values) < dims:
        values.extend(values)
    return values[:dims]


def embed_texts(texts: Iterable[str]) -> List[List[float]]:
    vectors: List[List[float]] = []
    for text in texts:
        text_hash = _hash_text(text)
        cached = _cached_embedding(text_hash)
        if cached is not None:
            vectors.append(cached)
            continue
        if not config.settings.llm_api_key:
            vector = _deterministic_embedding(text, config.settings.embedding_dims)
            _store_embedding(text_hash, vector)
            vectors.append(vector)
            continue
        payload = {"input": text, "model": config.settings.embed_model}
        headers = {"Authorization": f"Bearer {config.settings.llm_api_key}"}
        try:
            with httpx.Client(timeout=20) as client:
                response = client.post(
                    f"{config.settings.llm_base_url}/embeddings", json=payload, headers=headers
                )
                response.raise_for_status()
                data = response.json()
                vector = data["data"][0]["embedding"]
        except Exception as exc:  # noqa: BLE001 - surface error to logs
            logger.error("embedding_failed", extra={"error": str(exc)})
            vector = _deterministic_embedding(text, config.settings.embedding_dims)
        _store_embedding(text_hash, vector)
        vectors.append(vector)
    return vectors
