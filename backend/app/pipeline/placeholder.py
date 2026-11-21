"""Placeholder content for the steps that are not implemented yet.

Steps 3-9 arrive in phases 2-4. Until then they emit clearly labelled sample
progress so the stepper, the pauses and the report flow can be demonstrated.
Every event these steps publish carries ``placeholder: true`` and the UI
labels it; nothing here is presented as a real result.
"""

from __future__ import annotations

PLACEHOLDER_STEPS = frozenset({8, 9})

COUNTERS: dict[int, dict[str, int]] = {
    8: {"accepted": 0, "pending": 37},
    9: {"reports": 3},
}

MESSAGES: dict[int, list[str]] = {
    8: ["Uzman incelemesi bekleniyor"],
    9: [
        "Yönetici özeti taslaklanıyor",
        "PDF, Excel ve JSON çıktıları yazılıyor",
    ],
}
