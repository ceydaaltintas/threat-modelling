"""Schema for the mitigation catalogue.

A mitigation is a named control the platform can propose. Each one maps to
framework identifiers (ISO/IEC 27001:2022 Annex A, NIST SP 800-53, OWASP
ASVS) so a report can say which control family a recommendation belongs to.

Rule 7 of docs/PROMPT.md applies here: a clause number we cannot confirm is
left out rather than guessed. ISO mappings all carry
``verification: "needed"`` because the standard's text is paywalled and the
numbering must be checked against the organisation's own copy.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Framework = Literal["ISO 27001:2022", "NIST SP 800-53", "OWASP ASVS"]


class ControlMapping(BaseModel):
    model_config = ConfigDict(extra="forbid")

    framework: Framework
    # Identifier as it appears in the knowledge base, e.g. "A.8.24".
    id: str
    # "needed" when the clause number has not been confirmed from the source.
    verification: Literal["needed", "confirmed"] = "confirmed"


class Mitigation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^M-[A-Z0-9-]+$")
    title: str
    # What to actually do, in Turkish, one or two sentences.
    text: str
    # Grouping for the report.
    area: str = "genel"
    controls: list[ControlMapping] = Field(default_factory=list)
    # Rough implementation effort, shown in the report as a hint only.
    effort: Literal["düşük", "orta", "yüksek"] = "orta"


class MitigationFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mitigations: list[Mitigation]
