"""Compares vendor evidence without deciding legal eligibility or bid approval."""

import json
from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event
from src.services.tender_comparison_service import compare_vendor_evidence


class VendorCoverageNode(FunctionNode):
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        try:
            payload = json.loads(state.get("user_input") or "{}")
            profile = json.loads(payload.get("validated_profile") or "{}")
            requirements = json.loads(state.get("requirements_list") or "[]")
            if not isinstance(profile, dict) or not isinstance(requirements, list):
                raise ValueError("profile and requirements must use the expected shapes")
            coverage, gaps, flags = compare_vendor_evidence(requirements, profile)
        except (json.JSONDecodeError, TypeError, ValueError, KeyError) as exc:
            emit_trace_event("vendor_coverage_rejected", {"reason": str(exc)}, state)
            return {"status": AgentStatus.ERROR.value, "error_log": [f"VendorCoverageNode: {exc}"]}

        emit_trace_event(
            "vendor_coverage_compared",
            {"requirements": len(requirements), "manual_review_flags": len(flags)},
            state,
        )
        return {
            "coverage_scores": json.dumps(coverage),
            "gap_list": json.dumps(gaps),
            "mandatory_review_flags": json.dumps(flags),
            "status": AgentStatus.SUCCESS.value,
        }
