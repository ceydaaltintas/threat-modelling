"""Record the LLM answers the demo needs, once, so it can run offline.

Run this ONCE on a machine with internet and a working API key:

    docker compose exec backend python -m scripts.seed_demo

It runs each bundled sample scenario end to end with a live provider. Every
LLM call is written to ``llm_call``; afterwards ``DEMO_REPLAY=true`` answers
from those recordings and the demo needs neither internet nor quota.

What is recorded is the real answer the model gave - nothing is written by
hand. If a scenario fails (quota, network, schema), the script says so and
moves on to the next one rather than leaving you guessing.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.db import SessionLocal, engine  # noqa: E402
from app.core.samples import SAMPLE_SCENARIOS, SampleScenario  # noqa: E402
from app.core import storage  # noqa: E402
from app.models import (  # noqa: E402
    AnalysisRun,
    Document,
    LlmCall,
    Project,
    RunStep,
    Threat,
)
from app.pipeline import extract, runner  # noqa: E402
from app.pipeline.steps import PIPELINE_STEPS  # noqa: E402

# How long to wait for one scenario before giving up on it.
SCENARIO_TIMEOUT = 900
POLL_SECONDS = 3


def log(message: str) -> None:
    print(message, flush=True)


async def _create_run(scenario: SampleScenario) -> str:
    async with SessionLocal() as session:
        project = Project(
            name=f"{scenario.title} (kayıt)", sample_key=scenario.key
        )
        session.add(project)
        await session.flush()

        settings = get_settings()
        run = AnalysisRun(
            project_id=project.id,
            status="pending",
            llm_settings={
                "provider": settings.llm_provider,
                "model": settings.llm_model or None,
                "temperature": settings.llm_temperature,
            },
            demo_replay=settings.demo_replay,
            # No pauses: this is an unattended recording run.
            auto_continue=True,
        )
        session.add(run)
        await session.flush()

        for step in PIPELINE_STEPS:
            session.add(
                RunStep(
                    run_id=run.id, step_no=step.no, name=step.name, status="pending"
                )
            )

        document = Document(
            project_id=project.id,
            filename=scenario.filename,
            doc_type=extract.detect_doc_type(scenario.filename),
            mime_type="application/pdf",
            size_bytes=scenario.size_bytes,
        )
        session.add(document)
        await session.flush()
        document.storage_path = str(storage.copy_file(document.id, scenario.path))

        await session.commit()
        return run.id


async def _wait(run_id: str) -> tuple[str, str | None]:
    deadline = time.monotonic() + SCENARIO_TIMEOUT
    while time.monotonic() < deadline:
        await asyncio.sleep(POLL_SECONDS)
        async with SessionLocal() as session:
            run = await session.get(AnalysisRun, run_id)
            if run is None:
                return "missing", None
            if run.status in ("done", "failed", "cancelled"):
                return run.status, run.error_message
    return "timeout", f"{SCENARIO_TIMEOUT} saniyede tamamlanmadı."


async def _counts(run_id: str) -> dict[str, int]:
    async with SessionLocal() as session:
        threats = (
            await session.execute(
                select(func.count()).select_from(Threat).where(Threat.run_id == run_id)
            )
        ).scalar_one()
        live = (
            await session.execute(
                select(func.count())
                .select_from(LlmCall)
                .where(
                    LlmCall.run_id == run_id,
                    LlmCall.status == "ok",
                    LlmCall.from_cache.is_(False),
                )
            )
        ).scalar_one()
        cached = (
            await session.execute(
                select(func.count())
                .select_from(LlmCall)
                .where(LlmCall.run_id == run_id, LlmCall.from_cache.is_(True))
            )
        ).scalar_one()
        failed = (
            await session.execute(
                select(func.count())
                .select_from(LlmCall)
                .where(LlmCall.run_id == run_id, LlmCall.status != "ok")
            )
        ).scalar_one()
    return {"threats": threats, "live": live, "cached": cached, "failed": failed}


async def seed(only: str | None = None) -> int:
    settings = get_settings()
    log(f"Sağlayıcı: {settings.llm_provider} · model: {settings.llm_model or '—'}")
    if settings.demo_replay == "strict":
        log(
            "UYARI: DEMO_REPLAY=strict. Kayıt üretmek için canlı çağrı gerekir; "
            "bu modda yeni kayıt oluşmaz."
        )
    if settings.llm_provider == "stub":
        log(
            "UYARI: LLM_PROVIDER=stub. Stub sabit yanıt döndürür; üretilen "
            "kayıtlar gerçek bir demo için kullanılamaz."
        )

    scenarios = [s for s in SAMPLE_SCENARIOS if only in (None, s.key)]
    if not scenarios:
        log(f"Bilinmeyen senaryo: {only}")
        return 1

    failures = 0
    for index, scenario in enumerate(scenarios, start=1):
        log("")
        log(f"[{index}/{len(scenarios)}] {scenario.title} ({scenario.key})")
        if not scenario.available:
            log(f"  ATLANDI: örnek doküman bulunamadı ({scenario.filename}).")
            failures += 1
            continue

        started = time.monotonic()
        run_id = await _create_run(scenario)
        await runner.start(run_id)
        status, error = await _wait(run_id)
        counts = await _counts(run_id)
        seconds = round(time.monotonic() - started, 1)

        if status == "done":
            log(
                f"  TAMAM ({seconds} sn) · {counts['threats']} tehdit · "
                f"{counts['live']} canlı LLM çağrısı kaydedildi"
                + (f" · {counts['cached']} önbellekten" if counts["cached"] else "")
            )
        else:
            failures += 1
            log(f"  BAŞARISIZ ({status}, {seconds} sn): {error or '—'}")
            if counts["failed"]:
                log(f"  {counts['failed']} LLM çağrısı hata verdi.")

    async with SessionLocal() as session:
        total = (
            await session.execute(
                select(func.count())
                .select_from(LlmCall)
                .where(LlmCall.status == "ok", LlmCall.from_cache.is_(False))
            )
        ).scalar_one()

    log("")
    log(f"Veritabanındaki toplam kayıtlı yanıt: {total}")
    if failures:
        log(f"{failures} senaryo tamamlanamadı; yukarıdaki mesajlara bakın.")
    else:
        log("Tüm senaryolar kaydedildi. Artık .env içinde DEMO_REPLAY=true")
        log("yapıp internetsiz demo çalıştırabilirsiniz.")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scenario",
        help="Yalnızca bu örnek senaryoyu kaydet (örn. mobil-para-transferi).",
    )
    args = parser.parse_args()
    try:
        return asyncio.run(_run(args.scenario))
    except KeyboardInterrupt:
        log("Durduruldu.")
        return 130


async def _run(only: str | None) -> int:
    try:
        return await seed(only)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
