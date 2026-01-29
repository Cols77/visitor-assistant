from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from tourassist.app.models.schemas import TenantCreateRequest, TenantCreateResponse
from tourassist.app.models.db import get_connection
from tourassist.app.security.auth import create_tenant

router = APIRouter()


@router.post("/tenants", response_model=TenantCreateResponse)
def create_tenant_endpoint(payload: TenantCreateRequest) -> TenantCreateResponse:
    conn = get_connection()
    existing = conn.execute(
        "SELECT tenant_id FROM tenants WHERE tenant_id = ?",
        (payload.tenant_id,),
    ).fetchone()
    conn.close()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tenant already exists")
    data = create_tenant(payload.tenant_id)
    return TenantCreateResponse(**data)
