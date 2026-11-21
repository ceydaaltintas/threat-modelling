"""JSON exports.

Two shapes:

* **native** - everything the platform knows, including evidence, the risk
  breakdown, validation notes and the expert's decision. This is the format
  to use for re-import or for feeding another tool.
* **OTM** - Open Threat Model, for tools that read it. The mapping is
  best effort: OTM has no place for our evidence quotes or risk breakdown,
  so those are dropped. Anyone depending on it should check the mapping
  against the current OTM specification.
"""

from __future__ import annotations

from typing import Any

from app.reports.data import ReportData
from app.reports.pdf import DISCLAIMER, STRIDE_LABELS

OTM_VERSION = "0.2.0"

# STRIDE letter -> the category name used in the OTM export.
STRIDE_CATEGORY = {
    "S": "Spoofing",
    "T": "Tampering",
    "R": "Repudiation",
    "I": "Information Disclosure",
    "D": "Denial of Service",
    "E": "Elevation of Privilege",
}


def _threat_dict(data: ReportData, threat) -> dict[str, Any]:
    return {
        "id": threat.id,
        "title": threat.title,
        "stride": threat.stride,
        "stride_label": STRIDE_LABELS.get(threat.stride),
        "source": threat.source,
        "rule_id": threat.rule_id,
        "component_id": threat.component_ref,
        "component_name": data.component_name(threat.component_ref),
        "flow_id": threat.flow_ref,
        "description": threat.description,
        "scenario": threat.scenario,
        "evidence": threat.evidence or [],
        "is_assumption": threat.is_assumption,
        "knowledge_sources": threat.knowledge_sources or [],
        "ai_proposed": threat.ai_proposed,
        "system_calc": threat.system_calc,
        "expert": threat.expert,
        "review_status": threat.review_status,
        "validation_status": threat.validation_status,
        "validation_notes": [
            note
            for note in (threat.validation_notes or [])
            if note.get("code") != "rule_context"
        ],
        "mitigations": threat.mitigations or [],
        "control_mappings": threat.control_mappings or [],
    }


def build_native(data: ReportData) -> dict[str, Any]:
    return {
        "format": "threat-modelling-platform/v1",
        "disclaimer": DISCLAIMER,
        "project": {
            "name": data.project_name,
            "run_id": data.run_id,
            "generated_at": data.generated_at.isoformat(),
            "documents": data.documents,
            "llm": data.llm_settings,
            "demo_replay": data.demo_replay,
        },
        "counts": data.counts,
        "distribution": {
            "by_level": data.by_level,
            "by_stride": data.by_stride,
            "by_component": dict(data.by_component),
            "heatmap": data.heatmap,
        },
        "system_model": data.model.model_dump(mode="json"),
        "threats": [_threat_dict(data, threat) for threat in data.threats],
        "executive_summary": (
            {"text": data.summary_text, "ai_generated": data.summary_is_ai}
            if data.summary_text
            else None
        ),
        "notes": {
            "scoring": (
                "Risk puanı kod tarafından hesaplanır; LLM'in önerdiği değer "
                "ai_proposed alanında saklanır ve skora girmez."
            ),
            "iso_mappings": (
                "ISO 27001 madde eşlemeleri 'doğrulanacak' işaretlidir; "
                "kurumun kendi standart nüshasından teyit edilmelidir."
            ),
        },
    }


def build_otm(data: ReportData) -> dict[str, Any]:
    """Open Threat Model export (best effort - see module docstring)."""
    zones = [
        {
            "id": zone.id,
            "name": zone.name,
            "description": zone.description or "",
            "risk": {"trustRating": 10},
        }
        for zone in data.model.trust_zones
    ]
    zone_by_name = {zone.name: zone.id for zone in data.model.trust_zones}

    components = []
    for component in data.model.components:
        entry: dict[str, Any] = {
            "id": component.id,
            "name": component.name,
            "type": component.type,
            "description": component.description or "",
        }
        zone_id = zone_by_name.get(component.trust_zone or "")
        if zone_id:
            entry["parent"] = {"trustZone": zone_id}
        components.append(entry)

    dataflows = [
        {
            "id": flow.id,
            "name": (
                f"{data.component_name(flow.source_id)} → "
                f"{data.component_name(flow.target_id)}"
            ),
            "source": flow.source_id,
            "destination": flow.target_id,
            "description": flow.description or "",
            "attributes": {
                "protocol": flow.protocol or "unknown",
                "encrypted": str(flow.encrypted),
                "authenticated": str(flow.authenticated),
                "dataClasses": ", ".join(flow.data_classes),
            },
        }
        for flow in data.model.data_flows
    ]

    threats = []
    for threat in data.threats:
        calc = threat.system_calc or {}
        threats.append(
            {
                "id": threat.id,
                "name": threat.title,
                "description": threat.description or "",
                "categories": [STRIDE_CATEGORY.get(threat.stride, "Other")],
                "cwes": [
                    source["id"].replace("CWE-", "")
                    for source in (threat.knowledge_sources or [])
                    if source.get("id", "").startswith("CWE-")
                ],
                "risk": {
                    "likelihood": calc.get("likelihood", 0) * 20,
                    "impact": calc.get("impact", 0) * 20,
                },
                "attributes": {
                    "stride": threat.stride,
                    "level": calc.get("level", ""),
                    "score": calc.get("score", 0),
                    "reviewStatus": threat.review_status,
                    "isAssumption": str(threat.is_assumption),
                },
            }
        )

    mitigations: dict[str, dict] = {}
    for threat in data.threats:
        for item in threat.mitigations or []:
            mitigation_id = item.get("id")
            if mitigation_id and mitigation_id not in mitigations:
                mitigations[mitigation_id] = {
                    "id": mitigation_id,
                    "name": item.get("title") or mitigation_id,
                    "description": item.get("text") or "",
                    "riskReduction": 50,
                }

    return {
        "otmVersion": OTM_VERSION,
        "project": {
            "name": data.project_name,
            "id": data.run_id,
            "description": DISCLAIMER,
        },
        "trustZones": zones,
        "components": components,
        "dataflows": dataflows,
        "threats": threats,
        "mitigations": list(mitigations.values()),
    }
