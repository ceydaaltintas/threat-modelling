"""Append-only audit trail writer.

Every change made by a human (and every pipeline decision worth tracing) is
written here with old and new value. Rows are never updated or deleted.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


async def record(
    session: AsyncSession,
    *,
    actor: str,
    actor_role: str,
    action: str,
    object_type: str,
    object_id: str | None = None,
    run_id: str | None = None,
    old_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
    reason: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        at=datetime.now(tz=timezone.utc),
        actor=actor,
        actor_role=actor_role,
        action=action,
        object_type=object_type,
        object_id=object_id,
        run_id=run_id,
        old_value=old_value,
        new_value=new_value,
        reason=reason,
    )
    session.add(entry)
    await session.flush()
    return entry
