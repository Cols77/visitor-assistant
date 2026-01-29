from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, Header, HTTPException, status

from tourassist.app.models.db import get_connection


def generate_api_key() -> str:
    return secrets.token_urlsafe(32)


def create_tenant(tenant_id: str) -> dict[str, str]:
    api_key = generate_api_key()
    conn = get_connection()
    with conn:
        conn.execute(
            "INSERT INTO tenants (tenant_id, api_key, created_at) VALUES (?, ?, ?)",
            (tenant_id, api_key, datetime.now(timezone.utc).isoformat()),
        )
    conn.close()
    return {"tenant_id": tenant_id, "api_key": api_key}


def validate_api_key(tenant_id: str, api_key: str) -> bool:
    conn = get_connection()
    row = conn.execute(
        "SELECT api_key FROM tenants WHERE tenant_id = ?",
        (tenant_id,),
    ).fetchone()
    conn.close()
    return row is not None and secrets.compare_digest(row["api_key"], api_key)


def require_api_key(
    tenant_id: str,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> str:
    if not x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")
    if not validate_api_key(tenant_id, x_api_key):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key")
    return x_api_key


def enforce_api_key(tenant_id: str, api_key: Optional[str]) -> None:
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")
    if not validate_api_key(tenant_id, api_key):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key")
