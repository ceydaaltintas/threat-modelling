"""Loading and lookup for the mitigation catalogue."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

import yaml

from app.controls.schema import Mitigation, MitigationFile

logger = logging.getLogger(__name__)

CATALOG_PATH = Path(__file__).parent / "catalog.yaml"


@lru_cache(maxsize=1)
def load_mitigations() -> dict[str, Mitigation]:
    data = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8"))
    parsed = MitigationFile.model_validate(data)
    catalog = {item.id: item for item in parsed.mitigations}
    if len(catalog) != len(parsed.mitigations):
        raise ValueError("Önlem kataloğunda tekrar eden kimlik var.")
    logger.info("Önlem kataloğu yüklendi: %s önlem", len(catalog))
    return catalog


def get(mitigation_id: str) -> Mitigation | None:
    return load_mitigations().get(mitigation_id)


def control_mappings(mitigation_ids: list[str]) -> list[dict]:
    """Framework mappings for a set of mitigations, de-duplicated.

    Every ISO mapping carries ``verification: needed`` - the clause number
    has to be checked against the organisation's own copy of the standard
    before it goes into a report.
    """
    seen: dict[tuple[str, str], dict] = {}
    for mitigation_id in mitigation_ids:
        mitigation = get(mitigation_id)
        if mitigation is None:
            continue
        for control in mitigation.controls:
            key = (control.framework, control.id)
            seen.setdefault(
                key,
                {
                    "framework": control.framework,
                    "id": control.id,
                    "verification": control.verification,
                    "via": mitigation_id,
                },
            )
    return sorted(seen.values(), key=lambda item: (item["framework"], item["id"]))


def summary() -> dict:
    catalog = load_mitigations()
    by_area: dict[str, int] = {}
    for mitigation in catalog.values():
        by_area[mitigation.area] = by_area.get(mitigation.area, 0) + 1
    return {
        "total": len(catalog),
        "by_area": by_area,
        "control_ids": sorted(
            {control.id for m in catalog.values() for control in m.controls}
        ),
    }
