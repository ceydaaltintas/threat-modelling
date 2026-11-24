"""Hybrid retrieval over the passages of the uploaded document.

The same two engines the knowledge base uses - Postgres full text and
pgvector - fused the same way, but over what *this* document says rather
than over what is generally known. Step 3 asks it one question per
component and flow; step 4 uses the answers when the document is too long
to hand over whole.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.kb import embedding
from app.kb.loader import TS_CONFIG
from app.kb.search import RRF_K, _to_tsquery
from app.models import Document, DocumentChunk

logger = logging.getLogger(__name__)

CANDIDATES = 20


@dataclass
class PassageHit:
    text: str
    page: int | None
    section: str | None
    score: float
    matched_by: list[str]

    def as_dict(self) -> dict:
        return {
            "text": self.text,
            "page": self.page,
            "section": self.section,
            "score": round(self.score, 4),
            "matched_by": self.matched_by,
        }


async def search_document(
    session: AsyncSession,
    project_id: str,
    query: str,
    *,
    limit: int = 4,
) -> list[PassageHit]:
    """The passages of this project's documents that answer ``query``."""
    query = (query or "").strip()
    if not query:
        return []

    from sqlalchemy import func

    doc_ids = [
        row
        for (row,) in (
            await session.execute(
                select(Document.id).where(Document.project_id == project_id)
            )
        ).all()
    ]
    if not doc_ids:
        return []

    rows: dict[str, DocumentChunk] = {}
    ranks: dict[str, dict[str, int]] = {}

    def record(engine: str, ordered: list[DocumentChunk]) -> None:
        for position, row in enumerate(ordered, start=1):
            rows[row.id] = row
            ranks.setdefault(row.id, {})[engine] = position

    ts_query = _to_tsquery(query)
    if ts_query:
        rank = func.ts_rank(
            DocumentChunk.search_vector, func.to_tsquery(TS_CONFIG, ts_query)
        )
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id.in_(doc_ids))
            .where(
                DocumentChunk.search_vector.op("@@")(
                    func.to_tsquery(TS_CONFIG, ts_query)
                )
            )
            .order_by(rank.desc())
            .limit(CANDIDATES)
        )
        record("fulltext", (await session.execute(stmt)).scalars().all())

    try:
        vector = embedding.embed_query(query)
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id.in_(doc_ids))
            .where(DocumentChunk.embedding.is_not(None))
            .order_by(DocumentChunk.embedding.cosine_distance(vector))
            .limit(CANDIDATES)
        )
        record("vector", (await session.execute(stmt)).scalars().all())
    except Exception as exc:  # noqa: BLE001 - search degrades, never fails
        logger.info("Doküman vektör araması atlandı: %s", exc)

    scored: list[PassageHit] = []
    for chunk_id, positions in ranks.items():
        chunk = rows[chunk_id]
        score = sum(1.0 / (RRF_K + rank) for rank in positions.values())
        scored.append(
            PassageHit(
                text=chunk.text,
                page=chunk.page,
                section=chunk.section,
                score=score,
                matched_by=sorted(positions),
            )
        )
    scored.sort(key=lambda hit: hit.score, reverse=True)
    return scored[:limit]
