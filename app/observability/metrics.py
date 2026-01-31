from __future__ import annotations

from collections import deque
from statistics import median
from typing import Deque


class MetricsStore:
    def __init__(self, max_samples: int = 1000) -> None:
        self.latencies_ms: Deque[float] = deque(maxlen=max_samples)
        self.tokens_used: Deque[int] = deque(maxlen=max_samples)
        self.costs: Deque[float] = deque(maxlen=max_samples)

    def record_latency(self, latency_ms: float) -> None:
        self.latencies_ms.append(latency_ms)

    def record_tokens(self, tokens: int) -> None:
        self.tokens_used.append(tokens)

    def record_cost(self, cost: float) -> None:
        self.costs.append(cost)

    def percentile(self, values: Deque[float], pct: float) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        index = int(round((pct / 100) * (len(ordered) - 1)))
        return ordered[index]

    def latency_p50(self) -> float:
        if not self.latencies_ms:
            return 0.0
        return median(self.latencies_ms)

    def latency_p95(self) -> float:
        return self.percentile(self.latencies_ms, 95)


metrics_store = MetricsStore()
