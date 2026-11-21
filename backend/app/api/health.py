"""Health endpoints.

``/api/health/live`` answers without touching the database (container
liveness). ``/api/health`` also verifies the database connection and that the
migrations have been applied.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.schemas.api import HealthResponse

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("/live", response_model=HealthResponse)
async def live() -> HealthResponse:
    return HealthResponse(status="ok", database="not_checked")


@router.get("", response_model=HealthResponse)
async def health(session: AsyncSession = Depends(get_session)) -> HealthResponse:
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - reported to the operator
        return HealthResponse(
            status="degraded",
            database="unreachable",
            detail=f"Veritabanına ulaşılamadı: {exc}",
        )

    try:
        revision = (
            await session.execute(text("SELECT version_num FROM alembic_version"))
        ).scalar_one_or_none()
    except Exception:  # noqa: BLE001
        return HealthResponse(
            status="degraded",
            database="ok",
            migrations="missing",
            detail=(
                "Migration tablosu bulunamadı. 'alembic upgrade head' çalıştırın."
            ),
        )

    return HealthResponse(status="ok", database="ok", migrations=revision)
