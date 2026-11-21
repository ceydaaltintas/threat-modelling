"""The bundled sample scenarios shown on the "Yeni analiz" screen.

The documents live in ``/samples/documents`` (mounted read-only by
docker compose) and the expected findings in ``/samples/expected``. Phase 0
only lists them; phase 1 loads them through the real upload path.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

SAMPLES_ROOT = Path(os.environ.get("SAMPLES_DIR", "/samples"))


@dataclass(frozen=True)
class SampleScenario:
    key: str
    title: str
    doc_code: str
    summary: str
    # What this scenario is good at demonstrating.
    focus: str
    filename: str

    @property
    def path(self) -> Path:
        return SAMPLES_ROOT / "documents" / self.filename

    @property
    def available(self) -> bool:
        return self.path.is_file()

    @property
    def size_bytes(self) -> int | None:
        try:
            return self.path.stat().st_size
        except OSError:
            return None


SAMPLE_SCENARIOS: tuple[SampleScenario, ...] = (
    SampleScenario(
        key="mobil-para-transferi",
        title="Mobil Bankacılık – Para Transferi",
        doc_code="MB-TRF-AD-007",
        summary=(
            "Mobil uygulamadan başlatılan Havale/EFT/FAST transferleri; OTP ile "
            "kimlik doğrulama, limit ve dolandırıcılık kontrolü, çekirdek "
            "bankacılık entegrasyonu."
        ),
        focus="Ödeme akışı ve işlem bütünlüğü",
        filename="01_mobil_bankacilik_para_transferi.pdf",
    ),
    SampleScenario(
        key="kredi-basvuru",
        title="Bireysel Kredi Başvuru Platformu",
        doc_code="KRD-APP-SA-003",
        summary=(
            "Dijital kanallardan kredi başvurusu; uzaktan kimlik doğrulama, "
            "belge yükleme, OCR, otomatik karar motoru ve e-imza."
        ),
        focus="Veri gizliliği ve üçüncü taraflar",
        filename="02_bireysel_kredi_basvuru_platformu.pdf",
    ),
    SampleScenario(
        key="acik-bankacilik",
        title="Açık Bankacılık API Platformu",
        doc_code="OB-PLT-SA-001",
        summary=(
            "Üçüncü taraf sağlayıcılara (TPP) açılan hesap bilgisi ve ödeme "
            "başlatma API'leri; OAuth yetkilendirme, rıza yönetimi, webhook."
        ),
        focus="Kimlik doğrulama ve yetkilendirme",
        filename="03_acik_bankacilik_api_platformu.pdf",
    ),
)


def sample_by_key(key: str) -> SampleScenario | None:
    for scenario in SAMPLE_SCENARIOS:
        if scenario.key == key:
            return scenario
    return None
