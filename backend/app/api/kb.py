"""Knowledge base endpoints.

Phase 0 reports an empty knowledge base. Phase 2 fills it from
``backend/data/kb/*.jsonl`` and implements hybrid search (Postgres full-text
+ pgvector, merged with RRF).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.models import KbChunk
from app.schemas.api import KbStatsOut

router = APIRouter(prefix="/api/kb", tags=["kb"])


@router.get("/stats", response_model=KbStatsOut)
async def stats(session: AsyncSession = Depends(get_session)) -> KbStatsOut:
    total = (await session.execute(select(func.count()).select_from(KbChunk))).scalar_one()
    rows = (
        await session.execute(
            select(KbChunk.source, func.count()).group_by(KbChunk.source)
        )
    ).all()
    return KbStatsOut(
        total_chunks=total,
        by_source={source: count for source, count in rows},
        loaded=total > 0,
    )


@router.get("/search")
async def search(
    q: str = Query(min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
    session: AsyncSession = Depends(get_session)) -> dict:
    """Exact-identifier lookup only, until hybrid search lands in phase 2."""
    rows = (
        await session.execute(
            select(KbChunk).where(KbChunk.identifier.ilike(q.strip())).limit(limit)
        )
    ).scalars().all()
    return {
        "query": q,
        "mode": "exact_identifier",
        "note": (
            "Hibrit arama (anahtar kelime + vektör) Aşama 2'de devreye girecek."
        ),
        "results": [
            {
                "id": r.id,
                "source": r.source,
                "identifier": r.identifier,
                "title": r.title,
                "url": r.url,
                "license": r.license,
            }
            for r in rows
        ],
    }
