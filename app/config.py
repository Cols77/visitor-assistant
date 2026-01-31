from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    db_path: Path
    qdrant_url: str
    qdrant_collection: str
    llm_base_url: str
    llm_api_key: str | None
    llm_model: str
    embed_model: str
    embedding_dims: int
    max_chunk_chars: int
    top_k: int
    max_file_size_mb: int
    eval_timeout_s: int


_EMBED_MODEL_DIMS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}


def _resolve_embedding_dims(model: str) -> int:
    explicit = os.getenv("TOURASSIST_EMBED_DIMS")
    if explicit:
        return int(explicit)
    return _EMBED_MODEL_DIMS.get(model, 384)


load_dotenv()

_DEF_DATA_DIR = Path(os.getenv("TOURASSIST_DATA_DIR", "./data"))
_EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")

settings = Settings(
    data_dir=_DEF_DATA_DIR,
    db_path=Path(os.getenv("TOURASSIST_DB_PATH", _DEF_DATA_DIR / "tourassist.db")),
    qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333"),
    qdrant_collection=os.getenv("QDRANT_COLLECTION", "tourassist_chunks"),
    llm_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    llm_api_key=os.getenv("OPENAI_API_KEY"),
    llm_model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
    embed_model=_EMBED_MODEL,
    embedding_dims=_resolve_embedding_dims(_EMBED_MODEL),
    max_chunk_chars=int(os.getenv("TOURASSIST_MAX_CHUNK_CHARS", "800")),
    top_k=int(os.getenv("TOURASSIST_TOP_K", "4")),
    max_file_size_mb=int(os.getenv("TOURASSIST_MAX_FILE_SIZE_MB", "10")),
    eval_timeout_s=int(os.getenv("TOURASSIST_EVAL_TIMEOUT_S", "20")),
)

settings.data_dir.mkdir(parents=True, exist_ok=True)
