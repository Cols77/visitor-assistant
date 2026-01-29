from __future__ import annotations

from fastapi import FastAPI

from tourassist.app.api.chat import router as chat_router
from tourassist.app.api.ingest import router as ingest_router
from tourassist.app.api.metrics import router as metrics_router
from tourassist.app.api.tenants import router as tenants_router
from tourassist.app.models.db import init_db
from tourassist.app.observability.logger import configure_logging


configure_logging()
app = FastAPI(title="TourAssist")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


app.include_router(tenants_router)
app.include_router(ingest_router)
app.include_router(chat_router)
app.include_router(metrics_router)
