from __future__ import annotations

from collections import defaultdict, deque
from typing import Deque


class SessionMemory:
    def __init__(self, max_turns: int = 4) -> None:
        self._store: dict[str, Deque[dict[str, str]]] = defaultdict(lambda: deque(maxlen=max_turns * 2))

    def append(self, session_id: str, role: str, content: str) -> None:
        self._store[session_id].append({"role": role, "content": content})

    def get(self, session_id: str) -> list[dict[str, str]]:
        return list(self._store.get(session_id, []))


session_memory = SessionMemory()
