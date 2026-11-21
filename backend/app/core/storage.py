"""Where uploaded documents live on disk.

Files are stored under ``backend/uploads`` (git-ignored) with the document id
as the filename, so an uploaded name can never escape the directory.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

UPLOAD_ROOT = Path(os.environ.get("UPLOAD_DIR", "/app/uploads"))

# Hard ceiling regardless of MAX_UPLOAD_MB, to protect the demo machine.
ABSOLUTE_MAX_BYTES = 100 * 1024 * 1024


def ensure_root() -> Path:
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    return UPLOAD_ROOT


def path_for(document_id: str, filename: str) -> Path:
    suffix = Path(filename).suffix.lower()[:10]
    return ensure_root() / f"{document_id}{suffix}"


def save_bytes(document_id: str, filename: str, data: bytes) -> Path:
    target = path_for(document_id, filename)
    target.write_bytes(data)
    return target


def copy_file(document_id: str, source: Path) -> Path:
    target = path_for(document_id, source.name)
    shutil.copyfile(source, target)
    return target
