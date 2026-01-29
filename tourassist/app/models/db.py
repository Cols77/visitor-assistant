from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

from tourassist.app import config


SCHEMA_STATEMENTS: Iterable[str] = (
    """
    CREATE TABLE IF NOT EXISTS tenants (
        tenant_id TEXT PRIMARY KEY,
        api_key TEXT UNIQUE NOT NULL,
        created_at TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS documents (
        document_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        filename TEXT NOT NULL,
        content_hash TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE(tenant_id, content_hash)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS chunks (
        chunk_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        document_id TEXT NOT NULL,
        chunk_index INTEGER NOT NULL,
        text TEXT NOT NULL,
        qdrant_id TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS embeddings_cache (
        text_hash TEXT PRIMARY KEY,
        vector_json TEXT NOT NULL
    );
    """,
)


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or config.settings.db_path
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    with conn:
        for statement in SCHEMA_STATEMENTS:
            conn.execute(statement)
    conn.close()
