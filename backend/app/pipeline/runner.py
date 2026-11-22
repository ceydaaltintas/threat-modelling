"""Runs an analysis: real steps where they exist, placeholders elsewhere.

Phase 1 implements steps 1 and 2 for real. Steps 3-9 still emit labelled
sample progress (``app.pipeline.placeholder``) so the pause points and the
overall flow stay demonstrable.

Design notes:
  * each step is an independent coroutine with its own start/finish event and
    counters, and can be retried on its own (``retry_step``);
  * failures never crash the run: the step turns red with a Turkish,
    actionable message and the user can retry it;
  * the run waits for the user after step 2 (model approval) and at step 8,
    unless ``auto_continue`` is set.
"""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timezone
from typing import Awaitable, Callable

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.llm.base import LLMError
from app.llm.factory import build_client
from app.llm.gateway import LLMGateway
from sqlalchemy import select

from app.models import AnalysisRun, RunStep
from app.pipeline import (
    placeholder,
    progress,
    step1_documents,
    step2_system_model,
    step3_knowledge,
    step4_threats,
    step5_validation,
    step6_risk,
    step7_mitigations,
    step8_review,
    step9_report,
)
from app.pipeline.context import RunContext, StepFailed
from app.pipeline.steps import PIPELINE_STEPS, StepDefinition, step_by_no

logger = logging.getLogger(__name__)

# Steps that hand control to a human.
PAUSE_AFTER_STEP: dict[int, str] = {2: "model_approval", 8: "expert_review"}

StepRunner = Callable[[RunContext], Awaitable[dict[str, int]]]

REAL_STEPS: dict[int, StepRunner] = {
    1: step1_documents.run,
    2: step2_system_model.run,
    3: step3_knowledge.run,
    4: step4_threats.run,
    5: step5_validation.run,
    6: step6_risk.run,
    7: step7_mitigations.run,
    9: step9_report.run,
}

_resume_events: dict[str, asyncio.Event] = {}
_paused_at: dict[str, int] = {}
_tasks: dict[str, asyncio.Task[None]] = {}


def paused_at(run_id: str) -> int | None:
    return _paused_at.get(run_id)


def request_resume(run_id: str) -> bool:
    event = _resume_events.get(run_id)
    if event is None or event.is_set():
        return False
    event.set()
    return True


def is_running(run_id: str) -> bool:
    task = _tasks.get(run_id)
    return task is not None and not task.done()


async def _build_context(run_id: str) -> tuple[RunContext, AnalysisRun]:
    settings = get_settings()
    async with SessionLocal() as session:
        run = await session.get(AnalysisRun, run_id)
        if run is None:
            raise StepFailed("Analiz bulunamadı.")
        ctx = RunContext(
            run_id=run.id, project_id=run.project_id, settings=settings
        )
        detached = run
    try:
        ctx.gateway = LLMGateway(build_client(settings), run_id=run_id, settings=settings)
    except LLMError as exc:
        # Not fatal yet: steps that need the LLM will say so when reached.
        logger.warning("LLM istemcisi kurulamadı: %s", exc.message)
        ctx.gateway = None
    return ctx, detached


async def _run_step(ctx: RunContext, step: StepDefinition) -> bool:
    """Execute one step. Returns False when it failed."""
    started = progress.now()
    await progress.save_step(
        ctx.run_id,
        step.no,
        status="running",
        progress=0.0,
        message="Başlatılıyor…",
        started=True,
    )
    await progress.publish_step(
        ctx.run_id,
        step,
        "running",
        message="Başlatılıyor…",
        started_at=started,
        placeholder=step.no in placeholder.PLACEHOLDER_STEPS,
    )

    try:
        if step.no in REAL_STEPS:
            counters = await REAL_STEPS[step.no](ctx)
        else:
            counters = await _run_placeholder(ctx, step)
    except (StepFailed, LLMError) as exc:
        message = exc.message if hasattr(exc, "message") else str(exc)
        logger.warning("Adım %s başarısız: %s", step.no, message)
        await progress.save_step(
            ctx.run_id, step.no, status="failed", message=message, finished=True
        )
        await progress.publish_step(
            ctx.run_id,
            step,
            "failed",
            message=message,
            llm=ctx.llm_event(),
            started_at=started,
            finished_at=progress.now(),
        )
        await progress.save_run(ctx.run_id, status="failed", error_message=message)
        await progress.publish_run(ctx.run_id, "failed", message)
        return False
    except Exception as exc:  # noqa: BLE001 - never crash the run
        logger.exception("Adım %s beklenmeyen hata", step.no)
        message = f"Beklenmeyen hata: {exc}"
        await progress.save_step(
            ctx.run_id, step.no, status="failed", message=message, finished=True
        )
        await progress.publish_step(
            ctx.run_id, step, "failed", message=message, started_at=started,
            finished_at=progress.now(),
        )
        await progress.save_run(ctx.run_id, status="failed", error_message=message)
        await progress.publish_run(ctx.run_id, "failed", message)
        return False

    finished = progress.now()
    await progress.save_step(
        ctx.run_id,
        step.no,
        status="done",
        progress=1.0,
        message="Tamamlandı.",
        counters=counters,
        output=ctx.step_output.get(step.no),
        finished=True,
    )
    await progress.publish_step(
        ctx.run_id,
        step,
        "done",
        progress=1.0,
        message="Tamamlandı.",
        counters=counters,
        llm=ctx.llm_event(),
        started_at=started,
        finished_at=finished,
        placeholder=step.no in placeholder.PLACEHOLDER_STEPS,
    )
    return True


async def _run_placeholder(ctx: RunContext, step: StepDefinition) -> dict[str, int]:
    messages = placeholder.MESSAGES.get(step.no, [step.name])
    counters = placeholder.COUNTERS.get(step.no, {})
    for index, message in enumerate(messages, start=1):
        await asyncio.sleep(random.uniform(0.3, 0.7))
        ratio = index / len(messages)
        await ctx.report(
            step,
            progress_value=ratio,
            message=message,
            counters={k: max(1, int(v * ratio)) for k, v in counters.items()},
        )
    return counters


async def _wait_for_user(ctx: RunContext, step: StepDefinition, reason: str) -> None:
    await progress.save_run(ctx.run_id, status="waiting_user")
    event = asyncio.Event()
    _resume_events[ctx.run_id] = event
    _paused_at[ctx.run_id] = step.no
    await progress.publish_event(
        ctx.run_id,
        {
            "type": "pause",
            "step": step.no,
            "reason": reason,
            "message": (
                "Sistem modeli onayınızı bekliyor. İnceleyin, gerekiyorsa "
                "düzenleyin ve devam edin."
                if reason == "model_approval"
                else "Uzman incelemesi bekleniyor."
            ),
        },
    )
    await event.wait()
    _resume_events.pop(ctx.run_id, None)
    _paused_at.pop(ctx.run_id, None)
    await progress.save_run(ctx.run_id, status="running")
    await progress.publish_event(
        ctx.run_id,
        {
            "type": "resume",
            "step": step.no,
            "message": "Devam ediliyor.",
        },
    )
    # The run is no longer waiting on anyone: say so on the stream as well,
    # or the status badge stays on "Kullanıcı bekleniyor" for the rest of
    # the run.
    await progress.publish_run(ctx.run_id, "running", "Analiz sürüyor.")


async def _pipeline(run_id: str, *, from_step: int = 1) -> None:
    ctx, run = await _build_context(run_id)
    auto_continue = run.auto_continue

    await progress.save_run(run_id, status="running", error_message=None)
    if from_step == 1:
        await progress.save_run(run_id, started_at=progress.now())
    await progress.publish_run(
        run_id,
        "running",
        "Analiz başlatıldı." if from_step == 1 else f"{from_step}. adımdan devam ediliyor.",
    )

    for step in PIPELINE_STEPS:
        if step.no < from_step:
            continue

        # Step 8 is the expert's own work: it waits instead of running.
        if step.performer == "human":
            counts = await step8_review.snapshot(ctx)
            if not auto_continue:
                await progress.save_step(
                    run_id,
                    step.no,
                    status="waiting_user",
                    message=(
                        f"{counts['pending']} tehdit uzman kararı bekliyor."
                    ),
                    counters=counts,
                    output=ctx.step_output.get(step.no),
                    started=True,
                )
                await progress.publish_step(
                    run_id,
                    step,
                    "waiting_user",
                    message=f"{counts['pending']} tehdit uzman kararı bekliyor.",
                    counters=counts,
                )
                await _wait_for_user(
                    ctx, step, PAUSE_AFTER_STEP.get(step.no, "user_action")
                )
            # Re-read: the expert has been deciding while we waited.
            counts = await step8_review.snapshot(ctx)
            await progress.save_step(
                run_id,
                step.no,
                status="done",
                progress=1.0,
                message=(
                    f"{counts['decided']}/{counts['total']} tehdit için karar "
                    "verildi."
                ),
                counters=counts,
                output=ctx.step_output.get(step.no),
                finished=True,
            )
            await progress.publish_step(
                run_id,
                step,
                "done",
                progress=1.0,
                message=f"{counts['decided']}/{counts['total']} tehdit için karar verildi.",
                counters=counts,
            )
            continue

        if not await _run_step(ctx, step):
            return

        reason = PAUSE_AFTER_STEP.get(step.no)
        if reason == "model_approval":
            if auto_continue:
                await progress.publish_event(
                    run_id,
                    {
                        "type": "pause_skipped",
                        "step": step.no,
                        "reason": reason,
                        "message": "Otomatik devam açık; model onayı atlandı.",
                    },
                )
            else:
                await _wait_for_user(ctx, step, reason)

    await progress.save_run(run_id, status="done", finished_at=progress.now())
    await progress.publish_run(run_id, "done", "Analiz tamamlandı.")


async def start(run_id: str, *, from_step: int = 1) -> None:
    if is_running(run_id):
        return

    async def _guarded() -> None:
        try:
            await _pipeline(run_id, from_step=from_step)
        except asyncio.CancelledError:
            await progress.save_run(run_id, status="cancelled")
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Analiz hata ile durdu")
            await progress.save_run(run_id, status="failed", error_message=str(exc))
            await progress.publish_run(
                run_id, "failed", f"Analiz hata ile durdu: {exc}"
            )
        finally:
            _tasks.pop(run_id, None)

    _tasks[run_id] = asyncio.create_task(_guarded())


async def retry_step(run_id: str, step_no: int) -> None:
    """Re-run one step and continue from there."""
    step_by_no(step_no)  # raises for an unknown step
    await stop(run_id)
    await start(run_id, from_step=step_no)


async def stop(run_id: str) -> None:
    task = _tasks.get(run_id)
    if task and not task.done():
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):  # noqa: BLE001
            pass
    _resume_events.pop(run_id, None)
    _paused_at.pop(run_id, None)

    # With no live task - after a restart, say - cancelling the task cannot
    # end the run, so close it here. The open step is closed too, otherwise
    # the rail keeps a spinner on a step nothing is working on.
    async with SessionLocal() as session:
        run = await session.get(AnalysisRun, run_id)
        if run is None or run.status not in ("running", "waiting_user", "pending"):
            return
        run.status = "cancelled"
        run.finished_at = run.finished_at or datetime.now(timezone.utc)
        steps = (
            await session.execute(
                select(RunStep)
                .where(RunStep.run_id == run_id)
                .where(RunStep.status.in_(("running", "waiting_user")))
            )
        ).scalars().all()
        for step in steps:
            step.status = "failed"
            step.finished_at = step.finished_at or datetime.now(timezone.utc)
            step.message = "Analiz durduruldu."
        await session.commit()
    await progress.publish_run(run_id, "cancelled", "Analiz durduruldu.")
