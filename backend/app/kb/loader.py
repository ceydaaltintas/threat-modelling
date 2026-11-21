"""Load the pre-processed knowledge base into PostgreSQL.

``data/kb/*.jsonl`` ships with the repository, embeddings included, so the
demo machine needs no internet and no API key. Loading is idempotent: a row
is matched on (source, identifier, lang) and updated in place.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.models import KbChunk

logger = logging.getLogger(__name__)

KB_DIR = Path(__file__).resolve().parents[2] / "data" / "kb"

# Postgres has no Turkish text-search configuration; 'simple' indexes every
# token as-is, which is what we want for identifiers (CWE-89) and Turkish
# words alike. Stemming is handled by the vector side of the hybrid search.
TS_CONFIG = "simple"


def read_entries() -> list[dict]:
    entries: list[dict] = []
    for path in sorted(KB_DIR.glob("*.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
    return entries


def searchable_text(item: dict) -> str:
    tags = " ".join(item.get("tags") or [])
    return f"{item['identifier']} {item['title']} {item['text']} {tags}"


async def load(session: AsyncSession, *, replace: bool = False) -> dict[str, int]:
    entries = read_entries()
    if not entries:
        logger.warning("Bilgi tabanı dosyası bulunamadı: %s", KB_DIR)
        return {"inserted": 0, "updated": 0, "total": 0}

    if replace:
        await session.execute(text("DELETE FROM kb_chunk"))

    existing = {
        (row.source, row.identifier, row.lang): row
        for row in (await session.execute(select(KbChunk))).scalars().all()
    }

    inserted = updated = 0
    for item in entries:
        key = (item["source"], item["identifier"], item.get("lang", "tr"))
        row = existing.get(key)
        if row is None:
            row = KbChunk(
                source=item["source"],
                identifier=item["identifier"],
                lang=item.get("lang", "tr"),
            )
            session.add(row)
            inserted += 1
        else:
            updated += 1

        row.title = item["title"]
        row.text = item["text"]
        row.license = item.get("license")
        row.url = item.get("url") or None
        row.verification = item.get("verification")
        row.tags = item.get("tags") or []
        row.embedding = item.get("embedding")

    await session.flush()

    # Build the full-text index column in one pass.
    await session.execute(
        text(
            "UPDATE kb_chunk SET search_vector = to_tsvector("
            f"'{TS_CONFIG}', coalesce(identifier,'') || ' ' || coalesce(title,'') "
            "|| ' ' || coalesce(text,''))"
        )
    )
    await session.commit()

    total = (await session.execute(select(func.count()).select_from(KbChunk))).scalar_one()
    logger.info(
        "Bilgi tabanı yüklendi: %s yeni, %s güncellendi, toplam %s",
        inserted,
        updated,
        total,
    )
    return {"inserted": inserted, "updated": updated, "total": total}


async def ensure_loaded() -> dict[str, int]:
    """Load the knowledge base at startup when the table is empty."""
    async with SessionLocal() as session:
        count = (
            await session.execute(select(func.count()).select_from(KbChunk))
        ).scalar_one()
        if count:
            return {"inserted": 0, "updated": 0, "total": count}
        return await load(session)
