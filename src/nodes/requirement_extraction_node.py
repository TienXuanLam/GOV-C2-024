"""Extracts traceable tender requirements from normalized document chunks."""

import json
from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event
from src.services.tender_comparison_service import extract_requirements


class RequirementExtractionNode(FunctionNode):
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        try:
            payload = json.loads(state.get("user_input") or "{}")
            index = json.loads(payload.get("vector_index") or "{}")
            chunks = index.get("chunks", [])
            if not isinstance(chunks, list) or not chunks:
                raise ValueError("document chunks are missing")
            text = " ".join(chunk.get("chunk", "") for chunk in chunks if isinstance(chunk, dict))
            requirements = extract_requirements(text)
        except (json.JSONDecodeError, TypeError, ValueError, KeyError) as exc:
            emit_trace_event("requirement_extraction_rejected", {"reason": str(exc)}, state)
            return {"status": AgentStatus.ERROR.value, "error_log": [f"RequirementExtractionNode: {exc}"]}

        emit_trace_event("requirements_extracted", {"total_requirements": len(requirements)}, state)
        return {"requirements_list": json.dumps(requirements, ensure_ascii=False), "status": AgentStatus.SUCCESS.value}
