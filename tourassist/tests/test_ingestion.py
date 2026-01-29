from __future__ import annotations

from tourassist.app.models.db import get_connection
from tourassist.app.rag import ingestion


class FakeQdrant:
    def __init__(self) -> None:
        self.points = []

    def upsert(self, points):
        self.points.extend(points)


def test_ingestion_idempotent(monkeypatch):
    fake_qdrant = FakeQdrant()
    monkeypatch.setattr(ingestion, "get_qdrant", lambda: fake_qdrant)

    tenant_id = "tenant-1"
    filename = "guide.txt"
    data = b"Welcome to the city. The spa opens at 9am on Sundays."

    doc_id, chunks, status = ingestion.ingest_document(tenant_id, filename, data)
    assert status == "ready"
    assert chunks > 0
    assert fake_qdrant.points

    doc_id_2, chunks_2, status_2 = ingestion.ingest_document(tenant_id, filename, data)
    assert doc_id_2 == doc_id
    assert chunks_2 == 0
    assert status_2 == "ready"

    conn = get_connection()
    rows = conn.execute("SELECT document_id FROM documents WHERE tenant_id = ?", (tenant_id,)).fetchall()
    conn.close()
    assert len(rows) == 1
