import json

import pytest
from framework.errors import SecurityViolationError
from framework.schemas.agent_status import AgentStatus
from src.nodes.post_process_node import PostProcessNode


def _state(**updates):
    state = {
        "requirements_list": json.dumps([{"id": "REQ-001", "text": "technical", "type": "mandatory"}]),
        "coverage_scores": json.dumps([{"req_id": "REQ-001", "status": "evidence_found", "severity": "low"}]),
        "gap_list": "[]",
        "mandatory_review_flags": "[]",
    }
    state.update(updates)
    return state


def test_clean_evidence_package_is_only_ready_for_human_review():
    result = PostProcessNode().execute(_state())
    payload = json.loads(result["result"])
    assert result["status"] == AgentStatus.SUCCESS.value
    assert payload["review_signal"] == "ready_for_human_bid_review"
    assert "Disclaimer" in result["formatted_output"]


def test_mandatory_flag_routes_to_human_legal_review():
    result = PostProcessNode().execute(
        _state(mandatory_review_flags=json.dumps([{"req_id": "REQ-001", "reason": "missing"}]))
    )
    assert json.loads(result["result"])["review_signal"] == "manual_legal_and_procurement_review_required"


def test_output_gate_blocks_legal_determination():
    with pytest.raises(SecurityViolationError):
        PostProcessNode()._extra_security_gate_output({"formatted_output": "Vendor is eligible"})
