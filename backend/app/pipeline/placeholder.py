"""Placeholder content for the steps that are not implemented yet.

Steps 3-9 arrive in phases 2-4. Until then they emit clearly labelled sample
progress so the stepper, the pauses and the report flow can be demonstrated.
Every event these steps publish carries ``placeholder: true`` and the UI
labels it; nothing here is presented as a real result.
"""

from __future__ import annotations

PLACEHOLDER_STEPS = frozenset({5, 6, 7, 8, 9})

COUNTERS: dict[int, dict[str, int]] = {
    5: {"checked": 37, "flagged": 4},
    6: {"critical": 5, "high": 12},
    7: {"mitigations": 37, "mapped": 31},
    8: {"accepted": 0, "pending": 37},
    9: {"reports": 3},
}

MESSAGES: dict[int, list[str]] = {
    5: [
        "Bileşen referansları modelle karşılaştırılıyor",
        "Kaynak kimlikleri bilgi tabanında doğrulanıyor",
        "Tekrar eden tehditler benzerlikle aranıyor",
    ],
    6: [
        "Taban olasılık ve etki değerleri uygulanıyor",
        "Bağlam düzeltmeleri hesaplanıyor",
        "Seviye eşikleri uygulanıyor",
    ],
    7: [
        "Önlem metinleri hazırlanıyor",
        "Kontrol kataloğuna eşleniyor",
    ],
    8: ["Uzman incelemesi bekleniyor"],
    9: [
        "Yönetici özeti taslaklanıyor",
        "PDF, Excel ve JSON çıktıları yazılıyor",
    ],
}
