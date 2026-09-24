"""Builds a bounded advisory comparison report for human bid review."""

import json
from typing import Any, ClassVar

from framework.errors import SecurityViolationError
from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event
from src.schemas.state import PublicTenderDocumentComparisonState

_DISCLAIMER = (
    "\n\n---\n**免責事項 / Disclaimer:** "
    "本レポートは参考情報の提供を目的としたものであり、法的判断、入札資格判断、又は入札意思決定の代替となるものではありません。 "
    "This report is advisory evidence coverage only and is not a substitute for legal, eligibility, or bid decisions."
)
_SECRET_PATTERNS = ("sk-", "eyJ", "AKIA", "Bearer ", "password=", "secret=")
_PROHIBITED_DETERMINATIONS = (
    "is eligible",
    "not eligible",
    "eligibility confirmed",
    "bid approved",
    "bid rejected",
    "will be disqualified",
    "proceed to bid",
)


class PostProcessNode(FunctionNode):
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    def _extra_security_gate_output(self, result: dict[str, Any]) -> dict[str, Any]:
        rendered = json.dumps(result, ensure_ascii=False).lower()
        if any(pattern.lower() in rendered for pattern in _SECRET_PATTERNS):
            raise SecurityViolationError("PostProcessNode: credential-like content detected in output")
        if any(term in rendered for term in _PROHIBITED_DETERMINATIONS):
            raise SecurityViolationError("PostProcessNode: prohibited legal or bid determination detected")
        return result

    def execute(self, state: PublicTenderDocumentComparisonState) -> dict[str, Any]:
        try:
            requirements = json.loads(state.get("requirements_list") or "[]")
            coverage = json.loads(state.get("coverage_scores") or "[]")
            gaps = json.loads(state.get("gap_list") or "[]")
            flags = json.loads(state.get("mandatory_review_flags") or "[]")
            if not all(isinstance(value, list) for value in (requirements, coverage, gaps, flags)):
                raise ValueError("comparison state fields must be arrays")
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            emit_trace_event("comparison_report_rejected", {"reason": str(exc)}, state)
            return {"status": AgentStatus.ERROR.value, "error_log": [f"PostProcessNode: {exc}"]}

        coverage_by_id = {item.get("req_id"): item for item in coverage if isinstance(item, dict)}
        gap_by_id = {item.get("req_id"): item for item in gaps if isinstance(item, dict)}
        matrix = []
        for requirement in requirements:
            if not isinstance(requirement, dict):
                continue
            req_id = str(requirement.get("id", ""))
            match = coverage_by_id.get(req_id, {})
            gap = gap_by_id.get(req_id, {})
            matrix.append(
                {
                    "req_id": req_id,
                    "requirement": str(requirement.get("text", "")),
                    "type": str(requirement.get("type", "")),
                    "source_clause": str(requirement.get("source_clause", "")),
                    "coverage_status": str(match.get("status", "unknown")),
                    "severity": str(match.get("severity", gap.get("severity", ""))),
                    "evidence_note": str(match.get("vendor_evidence", "")),
                }
            )

        high_gaps = [gap for gap in gaps if isinstance(gap, dict) and gap.get("severity") == "high"]
        if flags:
            review_signal = "manual_legal_and_procurement_review_required"
        elif high_gaps:
            review_signal = "capability_gap_review_required"
        elif gaps:
            review_signal = "bid_team_evidence_review_required"
        else:
            review_signal = "ready_for_human_bid_review"

        result = {
            "comparison_matrix": matrix,
            "review_signal": review_signal,
            "gaps": gaps,
            "mandatory_review_flags": flags,
            "total_requirements": len(requirements),
        }
        rows = "\n".join(
            f"| {_cell(row['req_id'])} | {_cell(row['requirement'])} | {_cell(row['type'])} | "
            f"{_cell(row['coverage_status'])} | {_cell(row['severity'])} |"
            for row in matrix
        )
        table = "| Req ID | Requirement | Type | Evidence Coverage | Severity |\n" "|---|---|---|---|---|\n" + rows
        formatted = (
            f"# Tender Evidence Comparison Report\n\n{table}\n\n"
            f"## Human review signal\n\n`{review_signal}`{_DISCLAIMER}"
        )
        emit_trace_event(
            "comparison_report_generated",
            {"review_signal": review_signal, "total_requirements": len(requirements)},
            state,
        )
        return {
            "result": json.dumps(result, ensure_ascii=False),
            "formatted_output": formatted,
            "status": AgentStatus.SUCCESS.value,
        }


def _cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\r", " ").replace("\n", " ")[:160]
