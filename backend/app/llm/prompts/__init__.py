"""Versioned prompt files.

Prompts live as files (not inline strings) so they can be reviewed and
versioned. Each file has a ``# SİSTEM`` section and a ``# KULLANICI`` section;
``load_prompt`` splits them.

Never change a prompt in place once recorded LLM output exists for it: the
replay cache is keyed on the prompt text. Add a new ``.vN.md`` instead.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

PROMPT_DIR = Path(__file__).parent

_SYSTEM_MARKER = "# SİSTEM"
_USER_MARKER = "# KULLANICI"


@dataclass(frozen=True)
class Prompt:
    name: str
    system: str
    user_template: str

    def render(self, **values: object) -> str:
        return self.user_template.format(**values)


@lru_cache
def load_prompt(name: str) -> Prompt:
    path = PROMPT_DIR / f"{name}.md"
    if not path.is_file():
        raise FileNotFoundError(f"İstem dosyası bulunamadı: {path}")
    text = path.read_text(encoding="utf-8")

    if _SYSTEM_MARKER not in text or _USER_MARKER not in text:
        raise ValueError(
            f"{name}: istem dosyasında '{_SYSTEM_MARKER}' ve '{_USER_MARKER}' "
            "bölümleri bulunmalı."
        )

    _, rest = text.split(_SYSTEM_MARKER, 1)
    system, user = rest.split(_USER_MARKER, 1)
    return Prompt(name=name, system=system.strip(), user_template=user.strip())
