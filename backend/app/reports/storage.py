"""Where generated reports live on disk."""

from __future__ import annotations

import os
from pathlib import Path

REPORT_ROOT = Path(os.environ.get("REPORT_DIR", "/app/reports_out"))

# Only these names can be served, so a crafted path cannot escape.
ALLOWED = {
    "rapor.pdf": "application/pdf",
    "tehditler.xlsx": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ),
    "analiz.json": "application/json",
    "otm.json": "application/json",
}


def report_dir(run_id: str) -> Path:
    directory = REPORT_ROOT / run_id
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def report_path(run_id: str, name: str) -> Path | None:
    if name not in ALLOWED:
        return None
    path = report_dir(run_id) / name
    return path if path.is_file() else None
