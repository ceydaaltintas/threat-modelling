"""Phase 0 progress producer.

IMPORTANT: this module produces *placeholder* data so that the stepper, the
event log and the pause/resume flow can be built and demonstrated before the
real pipeline exists. The transport (asyncio task -> event broker -> SSE) and
the persistence (``run_step`` rows) are the real ones, so phases 1-4 replace
only the body of each step, not the plumbing.

Every event it emits carries ``placeholder: true`` so the UI can label it, and
no event ever claims to be a real LLM call.
"""

from __future__ import annotations

import asyncio
import random
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.events import broker
from app.core.samples import sample_by_key
from app.models import AnalysisRun, Project, RunStep
from app.pipeline.steps import PIPELINE_STEPS, StepDefinition

# Steps that hand control to a human. The run waits here until the user
# resumes it (or until auto_continue is on).
PAUSE_AFTER_STEP: dict[int, str] = {
    2: "model_approval",
    8: "expert_review",
}

# Placeholder counters per step, used only in phase 0.
_PLACEHOLDER_COUNTERS: dict[int, dict[str, int]] = {
    1: {"documents": 1, "pages": 2},
    2: {"components": 11, "flows": 14, "unknowns": 3},
    3: {"queries": 25, "sources": 63},
    4: {"rule_threats": 24, "llm_threats": 13, "threats": 37},
    5: {"checked": 37, "flagged": 4},
    6: {"critical": 5, "high": 12},
    7: {"mitigations": 37, "mapped": 31},
    8: {"accepted": 0, "pending": 37},
    9: {"reports": 3},
}

# Per-step progress messages (Turkish, user facing).
_PLACEHOLDER_MESSAGES: dict[int, list[str]] = {
    1: [
        "Dosya açılıyor: {filename}",
        "Sayfa 1/2 metni çıkarılıyor",
        "Sayfa 2/2 metni çıkarılıyor",
        "Bölüm başlıkları indeksleniyor",
    ],
    2: [
        "Bileşen tablosu okunuyor",
        "Güven bölgeleri eşleştiriliyor",
        "Veri akışları çıkarılıyor",
        "Her öğe için kanıt alıntısı bağlanıyor",
    ],
    3: [
        "Bilgi tabanında arama: API Geçidi",
        "Bilgi tabanında arama: Kimlik Doğrulama Servisi",
        "Bilgi tabanında arama: Transfer Servisi",
        "Sonuçlar RRF ile birleştiriliyor",
    ],
    4: [
        "Kural kataloğu çalıştırılıyor (40 kural)",
        "Bileşen 6/11 için tehdit üretiliyor: Transfer Servisi",
        "Bileşen 9/11 için tehdit üretiliyor: Operasyon Paneli",
        "Kural ve LLM tehditleri birleştiriliyor",
    ],
    5: [
        "Bileşen referansları modelle karşılaştırılıyor",
        "Kaynak kimlikleri bilgi tabanında doğrulanıyor",
        "Tekrar eden tehditler benzerlikle aranıyor",
    ],
    6: [
        "Taban olasılık ve etki değerleri uygulanıyor",
        "Bağlam düzeltmeleri hesaplanıyor (internete açık, veri sınıfı)",
        "Seviye eşikleri uygulanıyor",
    ],
    7: [
        "Önlem metinleri hazırlanıyor",
        "Kontrol kataloğuna eşleniyor (ISO 27001, NIST, ASVS)",
        "Emin olunmayan madde numaraları 'doğrulanacak' işaretleniyor",
    ],
    8: [
        "Uzman incelemesi bekleniyor",
    ],
    9: [
        "Yönetici özeti taslaklanıyor",
        "PDF raporu üretiliyor",
        "Excel ve JSON çıktıları yazılıyor",
    ],
}

# Resume signals, keyed by run id.
_resume_events: dict[str, asyncio.Event] = {}
# Which step a paused run is waiting on, keyed by run id.
_paused_at: dict[str, int] = {}
_tasks: dict[str, asyncio.Task[None]] = {}


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def paused_at(run_id: str) -> int | None:
    """Step number a run is currently waiting on, or None."""
    return _paused_at.get(run_id)


def request_resume(run_id: str) -> bool:
    """Release a paused run. Returns False when the run is not waiting."""
    event = _resume_events.get(run_id)
    if event is None or event.is_set():
        return False
    event.set()
    return True


def is_running(run_id: str) -> bool:
    task = _tasks.get(run_id)
    return task is not None and not task.done()


async def _publish_step(
    run_id: str,
    step: StepDefinition,
    status: str,
    *,
    progress: float = 0.0,
    message: str | None = None,
    counters: dict[str, int] | None = None,
    llm: dict[str, Any] | None = None,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
) -> None:
    # Timestamps travel with the event so the stepper can show per-step
    # durations without re-fetching the run after every update.
    await broker.publish(
        run_id,
        {
            "type": "step",
            "step": step.no,
            "step_name": step.name,
            "status": status,
            "progress": round(progress, 2),
            "message": message,
            "counters": counters or {},
            "llm": llm or {},
            "started_at": started_at.isoformat() if started_at else None,
            "finished_at": finished_at.isoformat() if finished_at else None,
            "placeholder": True,
        },
    )


async def _save_step(
    run_id: str,
    step_no: int,
    *,
    status: str,
    progress: float | None = None,
    message: str | None = None,
    counters: dict[str, int] | None = None,
    started: bool = False,
    finished: bool = False,
) -> None:
    async with SessionLocal() as session:
        row = (
            await session.execute(
                select(RunStep).where(
                    RunStep.run_id == run_id, RunStep.step_no == step_no
                )
            )
        ).scalar_one_or_none()
        if row is None:
            return
        row.status = status
        if progress is not None:
            row.progress = progress
        if message is not None:
            row.message = message
        if counters is not None:
            row.counters = counters
        if started:
            row.started_at = _now()
        if finished:
            row.finished_at = _now()
        await session.commit()


async def _save_run(run_id: str, **fields: Any) -> None:
    async with SessionLocal() as session:
        run = await session.get(AnalysisRun, run_id)
        if run is None:
            return
        for key, value in fields.items():
            setattr(run, key, value)
        await session.commit()


async def _load_run_flags(run_id: str) -> tuple[bool, str, str] | None:
    """Returns (auto_continue, demo_replay, document filename)."""
    async with SessionLocal() as session:
        run = await session.get(AnalysisRun, run_id)
        if run is None:
            return None
        project = await session.get(Project, run.project_id)
        scenario = (
            sample_by_key(project.sample_key)
            if project and project.sample_key
            else None
        )
        filename = scenario.filename if scenario else "yüklenen doküman"
        return run.auto_continue, run.demo_replay, filename


async def _run_pipeline(run_id: str) -> None:
    flags = await _load_run_flags(run_id)
    if flags is None:
        return
    auto_continue, demo_replay, filename = flags

    await _save_run(run_id, status="running", started_at=_now())
    await broker.publish(
        run_id,
        {
            "type": "run",
            "status": "running",
            "message": "Analiz başlatıldı (Aşama 0: örnek veriyle).",
            "placeholder": True,
        },
    )

    llm_calls = 0
    llm_tokens = 0

    for step in PIPELINE_STEPS:
        messages = [
            text.format(filename=filename)
            for text in _PLACEHOLDER_MESSAGES.get(step.no, [step.name])
        ]
        counters = _PLACEHOLDER_COUNTERS.get(step.no, {})

        # --- Human steps wait instead of running ---
        if step.performer == "human":
            started = _now()
            await _save_step(
                run_id,
                step.no,
                status="waiting_user",
                progress=0.0,
                message=messages[0],
                counters=counters,
                started=True,
            )
            await _save_run(run_id, status="waiting_user")
            await _publish_step(
                run_id,
                step,
                "waiting_user",
                message=messages[0],
                counters=counters,
                started_at=started,
            )
            if not auto_continue:
                event = asyncio.Event()
                _resume_events[run_id] = event
                _paused_at[run_id] = step.no
                await broker.publish(
                    run_id,
                    {
                        "type": "pause",
                        "step": step.no,
                        "reason": PAUSE_AFTER_STEP.get(step.no, "user_action"),
                        "message": "Kullanıcı işlemi bekleniyor.",
                        "placeholder": True,
                    },
                )
                await event.wait()
                _resume_events.pop(run_id, None)
                _paused_at.pop(run_id, None)
                await _save_run(run_id, status="running")
            await _save_step(
                run_id,
                step.no,
                status="done",
                progress=1.0,
                message="Uzman incelemesi tamamlandı.",
                counters={"accepted": 33, "pending": 0},
                finished=True,
            )
            await _publish_step(
                run_id,
                step,
                "done",
                progress=1.0,
                message="Uzman incelemesi tamamlandı.",
                counters={"accepted": 33, "pending": 0},
                started_at=started,
                finished_at=_now(),
            )
            continue

        # --- Automated step ---
        opening = "Başlatılıyor…"
        started = _now()
        await _save_step(
            run_id, step.no, status="running", progress=0.0, message=opening,
            started=True,
        )
        await _publish_step(
            run_id, step, "running", message=opening, started_at=started
        )

        total = len(messages)
        for index, message in enumerate(messages, start=1):
            await asyncio.sleep(random.uniform(0.35, 0.8))
            progress = index / total
            if step.performer in ("llm", "code+llm"):
                llm_calls += 1
                llm_tokens += random.randint(1200, 3600)
            partial = {
                key: max(1, int(value * progress)) for key, value in counters.items()
            }
            await _save_step(
                run_id, step.no, status="running", progress=progress, message=message,
                counters=partial,
            )
            await _publish_step(
                run_id,
                step,
                "running",
                progress=progress,
                message=message,
                counters=partial,
                llm={
                    "calls": llm_calls,
                    "cached": 0,
                    "tokens": llm_tokens,
                    "replay": demo_replay != "false",
                },
                started_at=started,
            )

        await _save_step(
            run_id,
            step.no,
            status="done",
            progress=1.0,
            message="Tamamlandı.",
            counters=counters,
            finished=True,
        )
        await _publish_step(
            run_id,
            step,
            "done",
            progress=1.0,
            message="Tamamlandı.",
            counters=counters,
            started_at=started,
            finished_at=_now(),
        )

        # --- Pause for model approval ---
        reason = PAUSE_AFTER_STEP.get(step.no)
        if reason == "model_approval":
            if auto_continue:
                await broker.publish(
                    run_id,
                    {
                        "type": "pause_skipped",
                        "step": step.no,
                        "reason": reason,
                        "message": "Otomatik devam açık; model onayı atlandı.",
                        "placeholder": True,
                    },
                )
            else:
                await _save_run(run_id, status="waiting_user")
                event = asyncio.Event()
                _resume_events[run_id] = event
                _paused_at[run_id] = step.no
                await broker.publish(
                    run_id,
                    {
                        "type": "pause",
                        "step": step.no,
                        "reason": reason,
                        "message": (
                            "Sistem modeli onayınızı bekliyor. İnceleyin, "
                            "gerekiyorsa düzenleyin ve devam edin."
                        ),
                        "placeholder": True,
                    },
                )
                await event.wait()
                _resume_events.pop(run_id, None)
                _paused_at.pop(run_id, None)
                await _save_run(run_id, status="running")
                await broker.publish(
                    run_id,
                    {
                        "type": "resume",
                        "step": step.no,
                        "message": "Model onaylandı, analiz sürüyor.",
                        "placeholder": True,
                    },
                )

    await _save_run(run_id, status="done", finished_at=_now())
    await broker.publish(
        run_id,
        {
            "type": "run",
            "status": "done",
            "message": "Analiz tamamlandı. Rapor hazır.",
            "placeholder": True,
        },
    )


async def start(run_id: str) -> None:
    """Start the placeholder pipeline for a run as a background task."""
    if is_running(run_id):
        return

    async def _guarded() -> None:
        try:
            await _run_pipeline(run_id)
        except asyncio.CancelledError:
            await _save_run(run_id, status="cancelled")
            raise
        except Exception as exc:  # noqa: BLE001 - surfaced to the user
            await _save_run(run_id, status="failed", error_message=str(exc))
            await broker.publish(
                run_id,
                {
                    "type": "run",
                    "status": "failed",
                    "message": f"Analiz hata ile durdu: {exc}",
                    "placeholder": True,
                },
            )
        finally:
            _tasks.pop(run_id, None)

    _tasks[run_id] = asyncio.create_task(_guarded())


async def stop(run_id: str) -> None:
    task = _tasks.get(run_id)
    if task and not task.done():
        task.cancel()
