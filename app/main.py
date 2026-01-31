from __future__ import annotations

from pathlib import Path
import logging
import time

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse

from app.api.chat import router as chat_router
from app.api.ingest import router as ingest_router
from app.api.metrics import router as metrics_router
from app.api.tenants import router as tenants_router
from app.models.db import init_db
from app.observability.logger import configure_logging


configure_logging()
app = FastAPI(title="TourAssist")
logger = logging.getLogger("uvicorn.access")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    client_host = request.client.host if request.client else "-"
    logger.info(
        "%s - \"%s %s\" %s %.2fms",
        client_host,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response

_APP_DIR = Path(__file__).resolve().parent
_UI_INDEX = _APP_DIR / "ui_index.html"
_UI_STYLES = _APP_DIR / "ui_styles.css"
_UI_APP = _APP_DIR / "ui_app.js"


@app.get("/")
def ui_root() -> FileResponse:
    return FileResponse(_UI_INDEX)


@app.get("/ui")
def ui_index() -> FileResponse:
    return FileResponse(_UI_INDEX)


@app.get("/ui/styles.css")
def ui_styles() -> FileResponse:
    return FileResponse(_UI_STYLES)


@app.get("/ui/app.js")
def ui_app() -> FileResponse:
    return FileResponse(_UI_APP)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


app.include_router(tenants_router)
app.include_router(ingest_router)
app.include_router(chat_router)
app.include_router(metrics_router)
