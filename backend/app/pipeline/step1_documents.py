"""Step 1 - read the uploaded documents.

Extracts text, indexes pages and sections, and stores the result on the
``document`` rows. Images (or PDFs with no text layer) are kept so step 2 can
hand them to the model's vision input.
"""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import delete, select, text

from app.core.db import SessionLocal
from app.kb import embedding
from app.kb.loader import TS_CONFIG
from app.models import Document, DocumentChunk
from app.pipeline import chunking, extract
from app.pipeline.context import RunContext, StepFailed
from app.pipeline.steps import step_by_no

logger = logging.getLogger(__name__)

STEP = step_by_no(1)

# Page images collected for step 2, keyed by run id.
_vision_images: dict[str, list[bytes]] = {}


def take_vision_images(run_id: str) -> list[bytes]:
    return _vision_images.pop(run_id, [])


async def _index_passages(session, document, result) -> int:
    """Cut the document into passages and index them for retrieval.

    Embeddings are computed locally on the CPU, so this costs time but no
    quota. A retry of step 1 replaces the document's own passages.
    """
    await session.execute(
        delete(DocumentChunk).where(DocumentChunk.document_id == document.id)
    )
    passages = chunking.split(
        result.full_text,
        pages=[(p.page, p.start, p.end) for p in result.pages],
        sections=[(s.label, s.start, s.end) for s in result.sections],
    )
    # Page headers and footers repeat in every passage and make one chunk
    # match every query; they carry no architecture.
    boilerplate = chunking.repeated_lines([p.text for p in result.pages])
    for passage in passages:
        passage.text = chunking.strip_lines(passage.text, boilerplate)
    passages = [p for p in passages if len(p.text) >= chunking.MIN_CHARS]
    if not passages:
        return 0

    try:
        vectors = embedding.embed_documents([p.text for p in passages])
    except Exception:  # noqa: BLE001 - search degrades to full text
        logger.warning("Doküman gömmeleri hesaplanamadı; yalnızca metin araması kullanılacak")
        vectors = [None] * len(passages)

    for passage, vector in zip(passages, vectors):
        session.add(
            DocumentChunk(
                document_id=document.id,
                page=passage.page,
                section=passage.section,
                ordinal=passage.ordinal,
                text=passage.text,
                embedding=vector,
            )
        )
    await session.flush()
    await session.execute(
        text(
            "UPDATE document_chunk SET search_vector = "
            f"to_tsvector('{TS_CONFIG}', coalesce(section,'') || ' ' || text) "
            "WHERE document_id = :doc"
        ),
        {"doc": document.id},
    )
    return len(passages)


async def run(ctx: RunContext) -> dict[str, int]:
    async with SessionLocal() as session:
        documents = (
            await session.execute(
                select(Document)
                .where(Document.project_id == ctx.project_id)
                .order_by(Document.created_at)
            )
        ).scalars().all()

        if not documents:
            raise StepFailed(
                "Bu analize ait doküman bulunamadı. Yeni analiz ekranından bir "
                "dosya yükleyin veya örnek senaryo seçin."
            )

        total_pages = 0
        total_chars = 0
        total_sections = 0
        total_chunks = 0
        images: list[bytes] = []

        for index, document in enumerate(documents, start=1):
            await ctx.report(
                STEP,
                progress_value=(index - 1) / len(documents),
                message=f"Dosya okunuyor: {document.filename}",
                counters={"documents": index - 1, "pages": total_pages},
            )

            path = Path(document.storage_path or "")
            if not path.is_file():
                raise StepFailed(
                    f"'{document.filename}' dosyası diskte bulunamadı. "
                    "Dosyayı yeniden yükleyin."
                )

            try:
                result = extract.extract(path, document.doc_type)
            except extract.UnsupportedDocument as exc:
                raise StepFailed(str(exc)) from exc
            except Exception as exc:  # noqa: BLE001 - surfaced to the user
                logger.exception("Metin çıkarma hatası: %s", document.filename)
                raise StepFailed(
                    f"'{document.filename}' okunamadı: {exc}",
                    detail=str(exc),
                ) from exc

            document.raw_text = result.full_text
            document.page_count = result.page_count
            document.section_map = result.to_section_map()
            document.extraction_note = result.note

            # Index the document for retrieval. A long document does not fit
            # in one prompt; step 3 fetches the passages that are about the
            # component being analysed instead of the first N characters.
            total_chunks += await _index_passages(session, document, result)

            total_pages += result.page_count
            total_chars += result.char_count
            total_sections += len(result.sections)
            images.extend(result.images)

            if result.needs_vision and not ctx.settings.ocr_enabled:
                logger.info(
                    "%s: metin katmanı yok, görsel okuma kullanılacak",
                    document.filename,
                )

        await session.commit()

    _vision_images[ctx.run_id] = images

    if total_chars < extract.MIN_CHARS_PER_PAGE and not images:
        raise StepFailed(
            "Dokümandan metin çıkarılamadı. Dosya taranmış bir görüntü ise "
            "OCR_ENABLED=true ile yeniden deneyin."
        )

    return {
        "documents": len(documents),
        "pages": total_pages,
        "sections": total_sections,
        "characters": total_chars,
        "passages": total_chunks,
    }
