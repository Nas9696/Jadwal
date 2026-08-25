import uuid
from typing import Annotated

from fastapi import Header, HTTPException, status

def tenant_context(x_tenant_id: Annotated[str | None, Header()] = None) -> uuid.UUID:
    if not x_tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Tenant-ID header is required")
    try:
        return uuid.UUID(x_tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid tenant identifier") from exc

