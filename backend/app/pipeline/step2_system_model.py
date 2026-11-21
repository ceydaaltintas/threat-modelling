"""Step 2 - extract the system model from the document text.

The LLM proposes the model; this module decides what is kept:
  * the answer must validate against the ``SystemModel`` schema (the gateway
    retries up to twice, feeding the error back);
  * flows pointing at components that do not exist are dropped and reported
    as assumptions rather than silently kept;
  * evidence quotes are checked against the document text - a quote that does
    not appear is marked, so a hallucinated citation cannot pass as evidence.

Long documents are processed in chunks and the partial models merged.
"""

from __future__ import annotations

import logging
import re
import unicodedata

from sqlalchemy import select

from app.core.db import SessionLocal
from app.llm.prompts import load_prompt
from app.models import Document, SystemModel as SystemModelRow
from app.pipeline.context import RunContext, StepFailed
from app.pipeline.step1_documents import take_vision_images
from app.pipeline.steps import step_by_no
from app.schemas.system_model import Assumption, SystemModel, merge_models

logger = logging.getLogger(__name__)

STEP = step_by_no(2)
PROMPT_NAME = "system_model_extraction.v1"

# Token budget per call, expressed in characters (roughly 4 chars per token).
MAX_CHARS_PER_CALL = 24_000
# A quote shorter than this is not worth verifying against the text.
MIN_QUOTE_CHARS = 12


async def run(ctx: RunContext) -> dict[str, int]:
    if ctx.gateway is None:
        raise StepFailed(
            "LLM sağlayıcısı yapılandırılmamış. Ayarlar ekranındaki sağlayıcı "
            "ve .env dosyasındaki LLM_API_KEY değerini kontrol edin."
        )

    async with SessionLocal() as session:
        documents = (
            await session.execute(
                select(Document)
                .where(Document.project_id == ctx.project_id)
                .order_by(Document.created_at)
            )
        ).scalars().all()

    if not documents:
        raise StepFailed("Önce 1. adımın tamamlanması gerekir.")

    title = ", ".join(d.filename for d in documents)
    page_count = sum(d.page_count or 0 for d in documents)
    document_text = _numbered_text(documents)
    images = take_vision_images(ctx.run_id)

    chunks = _chunk(document_text, MAX_CHARS_PER_CALL)
    prompt = load_prompt(PROMPT_NAME)
    partials: list[SystemModel] = []

    for index, chunk in enumerate(chunks, start=1):
        await ctx.report(
            STEP,
            progress_value=(index - 1) / (len(chunks) + 1),
            message=(
                f"Sistem modeli çıkarılıyor ({index}/{len(chunks)} bölüm)"
                if len(chunks) > 1
                else "Sistem modeli çıkarılıyor"
            ),
        )
        user = prompt.render(
            document_title=title,
            page_count=page_count or "bilinmiyor",
            document_text=chunk,
        )
        partials.append(
            await ctx.gateway.generate_json(
                prompt_name=PROMPT_NAME,
                system=prompt.system,
                user=user,
                schema=SystemModel,
                # Images only go with the first chunk; they are the whole doc.
                images=images if index == 1 else None,
                step_no=STEP.no,
            )
        )

    model = merge_models(partials) if len(partials) > 1 else partials[0]

    await ctx.report(
        STEP,
        progress_value=len(chunks) / (len(chunks) + 1),
        message="Kanıt alıntıları dokümanla karşılaştırılıyor",
    )
    stats = _post_process(model, document_text)

    if not model.components:
        raise StepFailed(
            "Dokümandan hiçbir bileşen çıkarılamadı. Doküman mimari içerik "
            "taşıyor mu kontrol edin veya adımı yeniden deneyin."
        )

    async with SessionLocal() as session:
        version = (
            await session.execute(
                select(SystemModelRow)
                .where(SystemModelRow.run_id == ctx.run_id)
                .order_by(SystemModelRow.version.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        session.add(
            SystemModelRow(
                run_id=ctx.run_id,
                version=(version.version + 1) if version else 1,
                data=model.model_dump(mode="json"),
                source="ai",
            )
        )
        await session.commit()

    return {
        "components": len(model.components),
        "flows": len(model.data_flows),
        "unknowns": len(model.unknowns),
        "assumptions": len(model.assumptions),
        **stats,
    }


def _numbered_text(documents: list[Document]) -> str:
    """Join documents with explicit page markers the model can cite."""
    parts: list[str] = []
    for document in documents:
        parts.append(f"=== DOSYA: {document.filename} ===")
        pages = [
            entry
            for entry in (document.section_map or [])
            if entry.get("type") == "page"
        ]
        text = document.raw_text or ""
        if not pages:
            parts.append(text)
            continue
        for page in pages:
            parts.append(f"[Sayfa {page['page']}]")
            parts.append(text[page["start"] : page["end"]])
    return "\n".join(parts)


def _chunk(text: str, budget: int) -> list[str]:
    """Split on page markers, never mid-page, keeping chunks under budget."""
    if len(text) <= budget:
        return [text]

    blocks = re.split(r"(?=\[Sayfa \d+\])", text)
    chunks: list[str] = []
    current = ""
    for block in blocks:
        if current and len(current) + len(block) > budget:
            chunks.append(current)
            current = block
        else:
            current += block
    if current.strip():
        chunks.append(current)
    return chunks or [text[:budget]]


def _normalise(value: str) -> str:
    """Casefold and collapse whitespace so quote matching is forgiving."""
    folded = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"\s+", " ", folded).strip()


def _post_process(model: SystemModel, document_text: str) -> dict[str, int]:
    """Drop impossible flows and flag evidence that is not in the document."""
    haystack = _normalise(document_text)

    dangling = model.dangling_flows()
    if dangling:
        known = ", ".join(flow.id for flow in dangling[:10])
        model.data_flows = [flow for flow in model.data_flows if flow not in dangling]
        model.assumptions.append(
            Assumption(
                text=(
                    f"{len(dangling)} veri akışı, modelde bulunmayan bir "
                    f"bileşene işaret ettiği için çıkarıldı ({known})."
                ),
                reason="Kod doğrulaması: akış uçları bileşen listesinde yok.",
            )
        )

    unverified = 0
    checked = 0
    for item in [*model.components, *model.data_flows]:
        for evidence in item.evidence:
            if len(evidence.quote) < MIN_QUOTE_CHARS:
                continue
            checked += 1
            if _normalise(evidence.quote) not in haystack:
                unverified += 1
                # Keep the quote but say plainly that it was not found.
                evidence.section = (
                    f"{evidence.section} · dokümanda bulunamadı"
                    if evidence.section
                    else "dokümanda bulunamadı"
                )

    without_evidence = len(model.without_evidence())
    if without_evidence:
        model.assumptions.append(
            Assumption(
                text=(
                    f"{without_evidence} öğe kanıt alıntısı taşımıyor; bunlar "
                    "varsayım olarak değerlendirilmelidir."
                ),
                reason="Kod doğrulaması: evidence listesi boş.",
            )
        )

    return {
        "evidence_checked": checked,
        "evidence_unverified": unverified,
        "without_evidence": without_evidence,
        "dropped_flows": len(dangling),
    }
