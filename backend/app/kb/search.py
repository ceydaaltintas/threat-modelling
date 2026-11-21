"""Hybrid retrieval over the knowledge base.

Three signals, merged with Reciprocal Rank Fusion:

  1. exact identifier match - a query that mentions "CWE-89" must return
     CWE-89 first, whatever the other signals say;
  2. Postgres full-text search over identifier + title + summary;
  3. pgvector cosine similarity against the local embedding.

RRF is used rather than score averaging because the two engines produce
scores on incomparable scales. Vector search is skipped (with a note) when
the embedding model is unavailable, so search degrades instead of failing.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.kb import embedding
from app.kb.loader import TS_CONFIG
from app.models import KbChunk

logger = logging.getLogger(__name__)

# RRF constant: larger values flatten the weight given to top ranks.
RRF_K = 60
# How many candidates each engine contributes before fusion.
CANDIDATES = 40
# An exact identifier hit is pinned above fused results.
IDENTIFIER_BONUS = 1.0

# "CWE-89", "API1:2023", "T1566", "A.8.3", "ASVS-V4", "LLM01"
_IDENTIFIER_PATTERN = re.compile(
    r"\b(?:CWE-\d+|CAPEC-\d+|T\d{4}(?:\.\d{3})?|API\d{1,2}:\d{4}|A\d{2}:\d{4}"
    r"|A\.\d+\.\d+|ASVS-V\d+|LLM\d{2}|STRIDE-[A-Z]+|LINDDUN-[A-Z]+"
    r"|[A-Z]{2}-\d+)\b",
    re.IGNORECASE,
)


@dataclass
class SearchHit:
    id: str
    source: str
    identifier: str
    title: str
    text: str
    url: str | None
    license: str | None
    verification: str | None
    score: float
    # Which engines found it, for the "why this result" line in the UI.
    matched_by: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "source": self.source,
            "identifier": self.identifier,
            "title": self.title,
            "text": self.text,
            "url": self.url,
            "license": self.license,
            "verification": self.verification,
            "score": round(self.score, 4),
            "matched_by": self.matched_by,
        }


def identifiers_in(query: str) -> list[str]:
    return [match.group(0).upper() for match in _IDENTIFIER_PATTERN.finditer(query)]


def _to_tsquery(query: str) -> str:
    """Build a safe OR-query; Postgres' own parser rejects stray punctuation."""
    tokens = re.findall(r"[\wçğıöşüÇĞİÖŞÜ.:-]+", query.lower())
    tokens = [token.strip(".:-") for token in tokens if len(token.strip(".:-")) > 1]
    return " | ".join(tokens) if tokens else ""


async def search(
    session: AsyncSession,
    query: str,
    *,
    limit: int = 10,
    sources: list[str] | None = None,
) -> tuple[list[SearchHit], dict]:
    """Returns (hits, diagnostics). Diagnostics drive the UI's explanation."""
    query = query.strip()
    if not query:
        return [], {"mode": "empty"}

    rows: dict[str, KbChunk] = {}
    ranks: dict[str, dict[str, int]] = {}

    def record(engine: str, ordered: list[KbChunk]) -> None:
        for position, row in enumerate(ordered, start=1):
            rows[row.id] = row
            ranks.setdefault(row.id, {})[engine] = position

    # --- 1. exact identifier ---
    wanted = identifiers_in(query)
    exact_ids: set[str] = set()
    if wanted:
        stmt = select(KbChunk).where(
            or_(*[func.upper(KbChunk.identifier) == value for value in wanted])
        )
        exact = (await session.execute(stmt)).scalars().all()
        record("identifier", exact)
        exact_ids = {row.id for row in exact}

    # --- 2. full text ---
    ts_query = _to_tsquery(query)
    if ts_query:
        rank = func.ts_rank(
            KbChunk.search_vector, func.to_tsquery(TS_CONFIG, ts_query)
        )
        stmt = (
            select(KbChunk)
            .where(KbChunk.search_vector.op("@@")(func.to_tsquery(TS_CONFIG, ts_query)))
            .order_by(rank.desc())
            .limit(CANDIDATES)
        )
        if sources:
            stmt = stmt.where(KbChunk.source.in_(sources))
        record("fulltext", (await session.execute(stmt)).scalars().all())

    # --- 3. vector ---
    vector_used = False
    try:
        vector = embedding.embed_query(query)
        stmt = (
            select(KbChunk)
            .where(KbChunk.embedding.is_not(None))
            .order_by(KbChunk.embedding.cosine_distance(vector))
            .limit(CANDIDATES)
        )
        if sources:
            stmt = stmt.where(KbChunk.source.in_(sources))
        record("vector", (await session.execute(stmt)).scalars().all())
        vector_used = True
    except embedding.EmbeddingUnavailable as exc:
        logger.warning("Vektör araması atlandı: %s", exc)

    # --- fusion ---
    hits: list[SearchHit] = []
    for row_id, engines in ranks.items():
        row = rows[row_id]
        score = sum(1 / (RRF_K + position) for position in engines.values())
        if row_id in exact_ids:
            score += IDENTIFIER_BONUS
        hits.append(
            SearchHit(
                id=row.id,
                source=row.source,
                identifier=row.identifier,
                title=row.title,
                text=row.text,
                url=row.url,
                license=row.license,
                verification=row.verification,
                score=score,
                matched_by=sorted(engines),
            )
        )

    hits.sort(key=lambda hit: (-hit.score, hit.identifier))
    diagnostics = {
        "mode": "hybrid" if vector_used else "fulltext_only",
        "exact_identifiers": wanted,
        "vector_search": vector_used,
        "candidates": len(hits),
        "note": None
        if vector_used
        else "Embedding modeli yüklenemedi; yalnızca anahtar kelime araması yapıldı.",
    }
    return hits[:limit], diagnostics


async def identifiers_exist(
    session: AsyncSession, identifiers: list[str]
) -> dict[str, bool]:
    """Which of these ids are in the knowledge base (step 5 uses this)."""
    if not identifiers:
        return {}
    wanted = [value.strip().upper() for value in identifiers if value and value.strip()]
    found = set(
        (
            await session.execute(
                select(func.upper(KbChunk.identifier)).where(
                    func.upper(KbChunk.identifier).in_(wanted)
                )
            )
        )
        .scalars()
        .all()
    )
    return {value: value in found for value in wanted}
