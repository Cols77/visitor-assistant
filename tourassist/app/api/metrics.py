from __future__ import annotations

from fastapi import APIRouter

from tourassist.app.observability.metrics import metrics_store

router = APIRouter()


@router.get("/metrics")
def metrics_endpoint() -> dict[str, float]:
    return {
        "latency_p50_ms": metrics_store.latency_p50(),
        "latency_p95_ms": metrics_store.latency_p95(),
    }
