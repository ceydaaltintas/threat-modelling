"""Audit trail endpoint (read only - rows are never changed or removed)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.models import AuditLog

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("")
async def list_audit(
    run_id: str | None = Query(default=None),
    action: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    stmt = select(AuditLog).order_by(AuditLog.at.desc()).limit(limit)
    if run_id:
        stmt = stmt.where(AuditLog.run_id == run_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    rows = (await session.execute(stmt)).scalars().all()
    return [
        {
            "id": r.id,
            "at": r.at,
            "actor": r.actor,
            "actor_role": r.actor_role,
            "action": r.action,
            "object_type": r.object_type,
            "object_id": r.object_id,
            "run_id": r.run_id,
            "old_value": r.old_value,
            "new_value": r.new_value,
            "reason": r.reason,
        }
        for r in rows
    ]
