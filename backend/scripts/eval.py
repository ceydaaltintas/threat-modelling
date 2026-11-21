"""Measure how much of the expected findings the platform catches.

    docker compose exec backend python -m scripts.eval            # kurallar
    docker compose exec backend python -m scripts.eval --live     # + LLM

Two modes:

* default ("fixture") - runs the rule catalogue against the hand-built system
  models in ``backend/tests/fixtures``. No LLM, no network, fully
  reproducible. This measures the **rule catalogue** alone.
* ``--live`` - runs the real pipeline on each sample document, so the
  measurement includes whatever the LLM extracted and proposed. Needs a
  provider (or recorded output with DEMO_REPLAY=true).

Results are written to ``eval/`` as JSON plus a short Markdown summary.

IMPORTANT: this is a measure of MODEL QUALITY on three fabricated documents,
not evidence of security effectiveness. The expected-findings list itself was
written by hand and has not been reviewed by a security professional.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone
from importlib import import_module
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.db import SessionLocal, engine  # noqa: E402
from app.core.samples import SAMPLE_SCENARIOS, sample_by_key  # noqa: E402
from app.rules.engine import evaluate, load_catalog  # noqa: E402
from app.schemas.system_model import SystemModel  # noqa: E402

EXPECTED_DIR = Path("/samples/expected")
# Mounted by docker compose from the project's ./eval folder.
OUTPUT_DIR = Path(os.environ.get("EVAL_DIR", "/eval"))
FIXTURE_MODULE = "tests.fixtures.{name}"
FIXTURE_ATTR = {
    "mobile_transfer_model": "MOBILE_TRANSFER_MODEL",
    "credit_application_model": "CREDIT_APPLICATION_MODEL",
    "open_banking_model": "OPEN_BANKING_MODEL",
}


def normalise(value: str) -> str:
    folded = unicodedata.normalize("NFKD", value or "")
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    folded = folded.replace("ı", "i")
    return re.sub(r"\s+", " ", folded.casefold()).strip()


def log(message: str) -> None:
    print(message, flush=True)


def load_expected() -> list[dict]:
    files = sorted(EXPECTED_DIR.glob("*.yaml"))
    if not files:
        raise SystemExit(f"Beklenen bulgu dosyası yok: {EXPECTED_DIR}")
    return [yaml.safe_load(path.read_text(encoding="utf-8")) for path in files]


def load_fixture(name: str) -> SystemModel:
    module = import_module(FIXTURE_MODULE.format(name=name))
    return SystemModel.model_validate(getattr(module, FIXTURE_ATTR[name]))


def document_text(sample_key: str) -> str:
    scenario = sample_by_key(sample_key)
    if scenario is None or not scenario.available:
        return ""
    import pymupdf

    with pymupdf.open(scenario.path) as document:
        return "\n".join(page.get_text() for page in document)


def match_finding(finding: dict, threats: list[dict]) -> dict:
    """A finding counts as caught when a rule fired or a title matches."""
    wanted = set(finding.get("rules") or [])
    by_rule = [t for t in threats if t.get("rule_id") in wanted]
    if by_rule:
        return {
            "caught": True,
            "how": "rule",
            "matched": sorted({t["rule_id"] for t in by_rule}),
            "example": by_rule[0]["title"],
        }

    keywords = [normalise(k) for k in finding.get("keywords") or []]
    for threat in threats:
        haystack = normalise(f"{threat['title']} {threat.get('description', '')}")
        hit = next((k for k in keywords if k and k in haystack), None)
        if hit:
            return {
                "caught": True,
                "how": "keyword",
                "matched": [hit],
                "example": threat["title"],
            }
    return {"caught": False, "how": None, "matched": [], "example": None}


def grade(expected: dict, threats: list[dict]) -> dict:
    results = []
    for finding in expected["findings"]:
        outcome = match_finding(finding, threats)
        results.append({**{k: finding[k] for k in ("id", "title")}, **outcome})

    caught = sum(1 for item in results if item["caught"])
    total = len(results)
    without_evidence = sum(1 for t in threats if not t.get("evidence"))
    flagged_ids = sum(
        1
        for t in threats
        for note in t.get("validation_notes", [])
        if note.get("code") == "unknown_knowledge_id"
    )
    return {
        "document": expected["document"],
        "sample_key": expected["sample_key"],
        "expected": total,
        "caught": caught,
        "recall": round(caught / total, 3) if total else 0.0,
        "threats": len(threats),
        "assumptions": without_evidence,
        "unknown_identifiers": flagged_ids,
        "findings": results,
    }


# --- fixture mode ------------------------------------------------------


def run_fixture_mode() -> list[dict]:
    reports = []
    for expected in load_expected():
        model = load_fixture(expected["fixture"])
        text = document_text(expected["sample_key"])
        threats = [
            {
                "rule_id": threat.rule_id,
                "title": threat.title,
                "description": threat.description,
                "evidence": threat.evidence,
                "validation_notes": [],
            }
            for threat in evaluate(model, text)
        ]
        reports.append(grade(expected, threats))
    return reports


# --- live mode ---------------------------------------------------------


async def run_live_mode() -> list[dict]:
    from sqlalchemy import select

    from app.models import AnalysisRun, Document, Project, RunStep, Threat
    from app.core import storage
    from app.pipeline import extract, runner
    from app.pipeline.steps import PIPELINE_STEPS

    reports = []
    for expected in load_expected():
        scenario = sample_by_key(expected["sample_key"])
        if scenario is None or not scenario.available:
            log(f"  ATLANDI: {expected['sample_key']} dokümanı yok.")
            continue

        async with SessionLocal() as session:
            project = Project(
                name=f"{scenario.title} (değerlendirme)", sample_key=scenario.key
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
                },
                demo_replay=settings.demo_replay,
                auto_continue=True,
            )
            session.add(run)
            await session.flush()
            for step in PIPELINE_STEPS:
                session.add(
                    RunStep(
                        run_id=run.id,
                        step_no=step.no,
                        name=step.name,
                        status="pending",
                    )
                )
            document = Document(
                project_id=project.id,
                filename=scenario.filename,
                doc_type=extract.detect_doc_type(scenario.filename),
                size_bytes=scenario.size_bytes,
            )
            session.add(document)
            await session.flush()
            document.storage_path = str(
                storage.copy_file(document.id, scenario.path)
            )
            await session.commit()
            run_id = run.id

        await runner.start(run_id)
        deadline = time.monotonic() + 900
        status = "timeout"
        while time.monotonic() < deadline:
            await asyncio.sleep(3)
            async with SessionLocal() as session:
                current = await session.get(AnalysisRun, run_id)
                if current and current.status in ("done", "failed", "cancelled"):
                    status = current.status
                    break

        async with SessionLocal() as session:
            rows = (
                await session.execute(
                    select(Threat).where(Threat.run_id == run_id)
                )
            ).scalars().all()
            threats = [
                {
                    "rule_id": t.rule_id,
                    "title": t.title,
                    "description": t.description or "",
                    "evidence": t.evidence or [],
                    "validation_notes": t.validation_notes or [],
                }
                for t in rows
            ]

        report = grade(expected, threats)
        report["run_id"] = run_id
        report["run_status"] = status
        reports.append(report)
        log(
            f"  {expected['sample_key']}: {report['caught']}/{report['expected']} "
            f"bulgu · {report['threats']} tehdit · durum {status}"
        )
    return reports


# --- output ------------------------------------------------------------


def write_output(reports: list[dict], mode: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(tz=timezone.utc)
    settings = get_settings()

    total_expected = sum(r["expected"] for r in reports)
    total_caught = sum(r["caught"] for r in reports)
    payload = {
        "generated_at": stamp.isoformat(),
        "mode": mode,
        "llm": {
            "provider": settings.llm_provider if mode == "live" else None,
            "model": settings.llm_model or None if mode == "live" else None,
            "demo_replay": settings.demo_replay if mode == "live" else None,
        },
        "rules_in_catalogue": len(load_catalog()),
        "totals": {
            "expected": total_expected,
            "caught": total_caught,
            "recall": round(total_caught / total_expected, 3)
            if total_expected
            else 0.0,
            "threats": sum(r["threats"] for r in reports),
        },
        "caveat": (
            "Bu ölçüm yalnızca model kalitesini gösterir; güvenlik "
            "etkinliğinin kanıtı değildir. Beklenen bulgu listesi elle "
            "hazırlanmıştır ve bir güvenlik uzmanı tarafından "
            "doğrulanmamıştır."
        ),
        "fixture_caveat": (
            "fixture kipinde sistem modelleri elle hazırlanmıştır: bu kip "
            "kural kataloğunun 'doğru bir sistem modeli verildiğinde' ne "
            "kadarını yakaladığını ölçer. Çıkarımın kendi kalitesini ölçmek "
            "için --live kipini kullanın."
        ),
        "documents": reports,
    }

    json_path = OUTPUT_DIR / f"eval-{mode}-{stamp.strftime('%Y%m%d-%H%M%S')}.json"
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = [
        "# Değerlendirme sonucu",
        "",
        f"- Tarih: {stamp.strftime('%d.%m.%Y %H:%M')} UTC",
        f"- Kip: {mode}" + (" (kurallar, LLM yok)" if mode == "fixture" else ""),
        f"- Kural kataloğu: {payload['rules_in_catalogue']} kural",
        f"- Toplam: **{total_caught}/{total_expected}** beklenen bulgu "
        f"(%{round(payload['totals']['recall'] * 100)})",
        "",
        "| Doküman | Yakalanan | Beklenen | Oran | Üretilen tehdit | Kanıtsız |",
        "|---|---|---|---|---|---|",
    ]
    for report in reports:
        lines.append(
            f"| {report['document']} | {report['caught']} | {report['expected']} "
            f"| %{round(report['recall'] * 100)} | {report['threats']} "
            f"| {report['assumptions']} |"
        )
    lines += ["", "## Yakalanamayan bulgular", ""]
    missed = [
        (report["sample_key"], finding)
        for report in reports
        for finding in report["findings"]
        if not finding["caught"]
    ]
    if missed:
        for sample_key, finding in missed:
            lines.append(f"- `{sample_key}` {finding['id']}: {finding['title']}")
    else:
        lines.append("Yok.")
    lines += [
        "",
        "---",
        "",
        payload["caveat"],
        "",
    ]
    if mode == "fixture":
        lines += [payload["fixture_caveat"], ""]
    md_path = OUTPUT_DIR / f"eval-{mode}-{stamp.strftime('%Y%m%d-%H%M%S')}.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")

    latest = OUTPUT_DIR / "son-sonuc.md"
    latest.write_text("\n".join(lines), encoding="utf-8")
    return md_path


async def main_async(live: bool) -> int:
    mode = "live" if live else "fixture"
    log(f"Değerlendirme kipi: {mode}")
    if live:
        settings = get_settings()
        log(
            f"  sağlayıcı: {settings.llm_provider} · "
            f"kayıtlı çıktı: {settings.demo_replay}"
        )
        reports = await run_live_mode()
    else:
        log("  Kural kataloğu, elle hazırlanmış sistem modelleri üzerinde.")
        reports = run_fixture_mode()

    if not reports:
        log("Değerlendirilecek doküman bulunamadı.")
        return 1

    path = write_output(reports, mode)
    total_expected = sum(r["expected"] for r in reports)
    total_caught = sum(r["caught"] for r in reports)
    log("")
    for report in reports:
        log(
            f"  {report['document']}: {report['caught']}/{report['expected']} "
            f"(%{round(report['recall'] * 100)}) · {report['threats']} tehdit"
        )
    log("")
    log(
        f"Toplam: {total_caught}/{total_expected} "
        f"(%{round(total_caught / total_expected * 100)})"
    )
    log(f"Çıktı: {path}")
    log("")
    log(
        "Bu ölçüm yalnızca model kalitesini gösterir; güvenlik etkinliğinin "
        "kanıtı değildir."
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Gerçek işlem hattını çalıştır (LLM gerekir).",
    )
    args = parser.parse_args()

    async def _run() -> int:
        try:
            return await main_async(args.live)
        finally:
            await engine.dispose()

    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
