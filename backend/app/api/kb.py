"""Knowledge base endpoints: statistics and hybrid search."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.kb import embedding, loader
from app.kb.search import search as hybrid_search
from app.models import KbChunk
from app.schemas.api import KbStatsOut

router = APIRouter(prefix="/api/kb", tags=["kb"])


@router.get("/stats", response_model=KbStatsOut)
async def stats(session: AsyncSession = Depends(get_session)) -> KbStatsOut:
    total = (
        await session.execute(select(func.count()).select_from(KbChunk))
    ).scalar_one()
    rows = (
        await session.execute(
            select(KbChunk.source, func.count()).group_by(KbChunk.source)
        )
    ).all()
    needs_check = (
        await session.execute(
            select(func.count())
            .select_from(KbChunk)
            .where(KbChunk.verification.is_not(None))
        )
    ).scalar_one()
    licences = (
        await session.execute(
            select(KbChunk.source, KbChunk.license).group_by(
                KbChunk.source, KbChunk.license
            )
        )
    ).all()

    return KbStatsOut(
        total_chunks=total,
        by_source={source: count for source, count in rows},
        loaded=total > 0,
        verification_needed=needs_check,
        licenses={source: licence or "—" for source, licence in licences},
        embedding_model=embedding.MODEL_NAME,
        vector_search=embedding.is_available(),
    )


@router.get("/search")
async def search(
    q: str = Query(min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
    source: list[str] | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    hits, diagnostics = await hybrid_search(
        session, q, limit=limit, sources=source
    )
    return {
        "query": q,
        "diagnostics": diagnostics,
        "results": [hit.as_dict() for hit in hits],
    }


@router.post("/reload")
async def reload_kb(session: AsyncSession = Depends(get_session)) -> dict:
    """Re-read data/kb/*.jsonl. Used after regenerating the content."""
    return await loader.load(session, replace=True)
