from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tourassist.app import config  # noqa: E402
from tourassist.app.config import Settings  # noqa: E402
from tourassist.app.models.db import init_db  # noqa: E402


@pytest.fixture(autouse=True)
def configure_test_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    test_settings = Settings(
        data_dir=data_dir,
        db_path=data_dir / "tourassist.db",
        qdrant_url="http://localhost:6333",
        qdrant_collection="test_chunks",
        llm_base_url="http://localhost:9999",
        llm_api_key=None,
        llm_model="gpt-4o-mini",
        embed_model="text-embedding-3-small",
        embedding_dims=384,
        max_chunk_chars=200,
        top_k=2,
        max_file_size_mb=10,
        eval_timeout_s=5,
    )
    monkeypatch.setattr(config, "settings", test_settings)
    init_db()
