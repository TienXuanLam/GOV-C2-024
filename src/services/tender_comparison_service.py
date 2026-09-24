"""Deterministic tender requirement and vendor-evidence comparison logic."""

from typing import Any

_TOPICS = ("technical", "financial", "certification", "schedule", "general", "eligibility")
_PUBLIC_PROCUREMENT_MARKERS = ("全省庁統一資格", "財政状況", "技術資格", "経営状況")


def extract_requirements(text: str) -> list[dict[str, str]]:
    requirements: list[dict[str, str]] = []
    for topic in _TOPICS:
        if topic in text.lower():
            requirements.append(
                {
                    "id": f"REQ-{len(requirements) + 1:03d}",
                    "text": f"{topic} requirement extracted from tender",
                    "type": "statutory_reference" if topic == "eligibility" else "mandatory",
                    "source_clause": f"Section: {topic}",
                    "law_ref": "会計法" if topic == "eligibility" else "",
                }
            )
    for marker in _PUBLIC_PROCUREMENT_MARKERS:
        if marker in text:
            requirements.append(
                {
                    "id": f"REQ-{len(requirements) + 1:03d}",
                    "text": f"Evidence requested for {marker}",
                    "type": "statutory_reference",
                    "source_clause": marker,
                    "law_ref": "会計法第29条の3",
                }
            )
    if not requirements:
        requirements.append(
            {
                "id": "REQ-001",
                "text": "General tender requirement",
                "type": "mandatory",
                "source_clause": "General",
                "law_ref": "",
            }
        )
    return requirements


def compare_vendor_evidence(
    requirements: list[dict[str, str]], vendor_profile: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, str]], list[dict[str, str]]]:
    searchable = str(vendor_profile).lower()
    coverage: list[dict[str, Any]] = []
    gaps: list[dict[str, str]] = []
    mandatory_flags: list[dict[str, str]] = []
    for requirement in requirements:
        tokens = [token.lower() for token in requirement["text"].split() if len(token) > 3]
        found = any(token in searchable for token in tokens)
        status = "evidence_found" if found else "evidence_not_found"
        severity = (
            "low" if found else "high" if requirement["type"] in {"mandatory", "statutory_reference"} else "medium"
        )
        item = {
            "req_id": requirement["id"],
            "status": status,
            "vendor_evidence": "Matching profile evidence located" if found else "No matching evidence located",
            "severity": severity,
        }
        coverage.append(item)
        if not found:
            gaps.append(
                {
                    "req_id": requirement["id"],
                    "gap_description": "Supporting evidence was not located in the supplied vendor profile",
                    "severity": severity,
                }
            )
            if requirement["type"] in {"mandatory", "statutory_reference"}:
                mandatory_flags.append(
                    {
                        "req_id": requirement["id"],
                        "reason": "mandatory_or_statutory_evidence_not_located",
                        "law_ref": requirement.get("law_ref", ""),
                    }
                )
    return coverage, gaps, mandatory_flags
