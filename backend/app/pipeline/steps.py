"""The nine pipeline steps.

This module is the single source of truth for step numbers, their Turkish
screen labels and who performs them. The API exposes it so the frontend
stepper never hard-codes the list.

Phase 0 only declares the steps; the executable modules arrive in later
phases (one module per step).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Performer = Literal["code", "llm", "code+llm", "human"]

# The pipeline pauses for human approval of the system model after step 2.
MODEL_APPROVAL_AFTER_STEP = 2


@dataclass(frozen=True)
class StepDefinition:
    no: int
    # Label shown in the stepper (Turkish - user facing).
    name: str
    # One line describing what the step does (Turkish).
    description: str
    performer: Performer
    # Counter keys this step is expected to report, e.g. {"components": "bileşen"}
    counter_labels: dict[str, str]


PIPELINE_STEPS: tuple[StepDefinition, ...] = (
    StepDefinition(
        no=1,
        name="Doküman okundu",
        description=(
            "Dosyalardan metin çıkarılır, sayfa ve bölümler indekslenir. "
            "Görsel varsa LLM ile okunur (veya OCR yedeği)."
        ),
        performer="code+llm",
        counter_labels={
            "documents": "doküman",
            "pages": "sayfa",
            "sections": "bölüm",
            "characters": "karakter",
        },
    ),
    StepDefinition(
        no=2,
        name="Sistem modeli çıkarıldı",
        description=(
            "Metinden bileşenler, veri akışları, güven bölgeleri ve hassas "
            "veriler çıkarılır; her öğeye kanıt eklenir."
        ),
        performer="llm",
        counter_labels={
            "components": "bileşen",
            "flows": "akış",
            "unknowns": "belirsiz",
            "assumptions": "varsayım",
            "evidence_checked": "kanıt denetlendi",
            "evidence_unverified": "kanıt doğrulanamadı",
            "without_evidence": "kanıtsız",
            "dropped_flows": "elenen akış",
        },
    ),
    StepDefinition(
        no=3,
        name="İlgili bilgi toplandı",
        description=(
            "Her bileşen ve akış için bilgi tabanında hibrit arama yapılır "
            "(anahtar kelime + vektör, RRF ile birleştirme)."
        ),
        performer="code",
        counter_labels={"queries": "sorgu", "sources": "kaynak"},
    ),
    StepDefinition(
        no=4,
        name="Tehditler üretildi",
        description=(
            "Kural kataloğu bilinen tehditleri üretir; LLM bağlama özel ek "
            "tehditler önerir. İkisi birleştirilir."
        ),
        performer="code+llm",
        counter_labels={
            "threats": "tehdit",
            "rule_threats": "kuraldan",
            "llm_threats": "AI'dan",
            "merged": "birleştirilmiş",
        },
    ),
    StepDefinition(
        no=5,
        name="Doğrulama",
        description=(
            "Bileşen modelde var mı, STRIDE geçerli mi, kaynak kimlikleri "
            "bilgi tabanında var mı, tekrar var mı. Başarısızlar elenmez, "
            "işaretlenir."
        ),
        performer="code",
        counter_labels={
            "checked": "kontrol",
            "flagged": "işaretli",
            "unknown_ids": "bilinmeyen kimlik",
            "duplicates": "tekrar",
            "evidence_missing": "kanıt bulunamadı",
        },
    ),
    StepDefinition(
        no=6,
        name="Risk hesaplandı",
        description=(
            "Olasılık × etki (1–5) hesaplanır; bağlam düzeltmeleri uygulanır "
            "ve kırılım ekranda açıklanır."
        ),
        performer="code",
        counter_labels={
            "critical": "kritik",
            "high": "yüksek",
            "medium": "orta",
            "low": "düşük",
        },
    ),
    StepDefinition(
        no=7,
        name="Önlemler önerildi",
        description=(
            "Tehdide ve teknolojiye uygun önlem metni üretilir, kontrol "
            "kataloğuna eşlenir."
        ),
        performer="code+llm",
        counter_labels={
            "mitigations": "önlem",
            "mapped": "kontrol eşlemesi",
            "llm_written": "AI metni",
        },
    ),
    StepDefinition(
        no=8,
        name="Uzman incelemesi",
        description=(
            "Güvenlik uzmanı tehditleri kabul eder, reddeder, düzenler veya "
            "yanlış pozitif işaretler. Her işlem denetim izine yazılır."
        ),
        performer="human",
        counter_labels={
            "total": "tehdit",
            "decided": "karar verildi",
            "pending": "bekleyen",
            "accepted": "kabul",
            "rejected": "red",
            "false_positive": "yanlış pozitif",
            "edited": "düzenlendi",
        },
    ),
    StepDefinition(
        no=9,
        name="Rapor hazır",
        description=(
            "PDF yönetici raporu, Excel tehdit listesi ve JSON dışa aktarma "
            "üretilir."
        ),
        performer="code+llm",
        counter_labels={"reports": "rapor"},
    ),
)


def step_by_no(no: int) -> StepDefinition:
    for step in PIPELINE_STEPS:
        if step.no == no:
            return step
    raise KeyError(f"Unknown pipeline step: {no}")
