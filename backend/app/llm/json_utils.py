"""Helpers for getting valid JSON out of a model response."""

from __future__ import annotations

import json
import re
from typing import Any

_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def extract_json(text: str) -> Any:
    """Parse JSON from a model answer, tolerating code fences and preamble.

    Raises ``ValueError`` when nothing parseable is found; the caller turns
    that into a repair attempt.
    """
    candidate = text.strip()
    if not candidate:
        raise ValueError("Model boş yanıt döndürdü.")

    fenced = _FENCE.search(candidate)
    if fenced:
        candidate = fenced.group(1).strip()

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    # Fall back to the outermost {...} or [...] block.
    for opener, closer in (("{", "}"), ("[", "]")):
        start = candidate.find(opener)
        end = candidate.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(candidate[start : end + 1])
            except json.JSONDecodeError:
                continue

    raise ValueError("Model yanıtı JSON olarak çözümlenemedi.")
