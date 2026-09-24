import json
import inspect

from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from src.nodes.pre_process_node import PreProcessNode


def _base_state(**kwargs) -> dict:
    return {
        "user_input": "",
        "correlation_id": "test-corr",
        "session_id": "test-session",
        "thread_id": "test-thread",
        "trace_id": "",
        "caller_trust_level": TrustLevel.VERIFIED_EXTERNAL.value,
        "caller_id": "",
        "hitl_allowed": True,
        "node_history": [],
        "error_log": [],
        **kwargs,
    }


def _valid_input(doc_count: int = 1) -> str:
    return json.dumps(
        {
            "tender_documents": [
                {"id": f"doc{i}", "type": "txt", "text": f"Tender requirement section {i}. technical financial."}
                for i in range(doc_count)
            ],
            "vendor_profile": {"name": "Test Corp", "certifications": ["ISO9001"]},
        }
    )


class TestPreProcessNodeSuccess:
    def test_valid_input_returns_success(self):
        node = PreProcessNode()
        state = _base_state(user_input=_valid_input())
        result = node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS.value

    def test_returns_vector_index(self):
        node = PreProcessNode()
        state = _base_state(user_input=_valid_input())
        result = node.execute(state)
        idx = json.loads(result["vector_index"])
        assert "chunks" in idx
        assert idx["document_count"] == 1

    def test_returns_validated_profile(self):
        node = PreProcessNode()
        state = _base_state(user_input=_valid_input())
        result = node.execute(state)
        profile = json.loads(result["validated_profile"])
        assert profile["name"] == "Test Corp"

    def test_document_count_field(self):
        node = PreProcessNode()
        state = _base_state(user_input=_valid_input(doc_count=2))
        result = node.execute(state)
        assert result["document_count"] == 2

    def test_multiple_documents_chunked(self):
        node = PreProcessNode()
        state = _base_state(user_input=_valid_input(doc_count=3))
        result = node.execute(state)
        idx = json.loads(result["vector_index"])
        assert idx["document_count"] == 3
        assert idx["total_chunks"] >= 3


class TestPreProcessNodeErrors:
    def test_empty_input_returns_error(self):
        node = PreProcessNode()
        state = _base_state(user_input="")
        result = node.execute(state)
        assert result["status"] == AgentStatus.ERROR.value

    def test_non_json_input_returns_error(self):
        node = PreProcessNode()
        state = _base_state(user_input="not json")
        result = node.execute(state)
        assert result["status"] == AgentStatus.ERROR.value

    def test_missing_tender_documents_returns_error(self):
        node = PreProcessNode()
        state = _base_state(user_input=json.dumps({"vendor_profile": {"name": "Corp"}}))
        result = node.execute(state)
        assert result["status"] == AgentStatus.ERROR.value

    def test_empty_tender_documents_returns_error(self):
        node = PreProcessNode()
        state = _base_state(
            user_input=json.dumps(
                {
                    "tender_documents": [],
                    "vendor_profile": {"name": "Corp"},
                }
            )
        )
        result = node.execute(state)
        assert result["status"] == AgentStatus.ERROR.value

    def test_missing_vendor_profile_returns_error(self):
        node = PreProcessNode()
        state = _base_state(
            user_input=json.dumps(
                {
                    "tender_documents": [{"id": "d1", "type": "txt", "text": "req"}],
                    "vendor_profile": {},
                }
            )
        )
        result = node.execute(state)
        assert result["status"] == AgentStatus.ERROR.value

    def test_unsupported_document_type_returns_error(self):
        node = PreProcessNode()
        state = _base_state(
            user_input=json.dumps(
                {
                    "tender_documents": [{"id": "d1", "type": "xls", "text": "req"}],
                    "vendor_profile": {"name": "Corp"},
                }
            )
        )
        result = node.execute(state)
        assert result["status"] == AgentStatus.ERROR.value

    def test_too_many_documents_returns_error(self):
        node = PreProcessNode()
        state = _base_state(
            user_input=json.dumps(
                {
                    "tender_documents": [{"id": f"d{i}", "type": "txt", "text": "req"} for i in range(11)],
                    "vendor_profile": {"name": "Corp"},
                }
            )
        )
        result = node.execute(state)
        assert result["status"] == AgentStatus.ERROR.value


class TestPreProcessNodeSecurity:
    def test_s2_rejects_pii_my_number(self):
        node = PreProcessNode()
        state = _base_state(user_input='{"pii": "1234-5678-9012"}')
        result = node._extra_security_gate_input(state)
        assert result.get("status") == AgentStatus.ERROR.value

    def test_s2_rejects_classified_marker(self):
        node = PreProcessNode()
        state = _base_state(user_input='{"content": "機密情報"}')
        result = node._extra_security_gate_input(state)
        assert result.get("status") == AgentStatus.ERROR.value

    def test_s2_passes_clean_input(self):
        node = PreProcessNode()
        state = _base_state(user_input='{"tender_documents": [], "vendor_profile": {}}')
        result = node._extra_security_gate_input(state)
        assert result.get("status") != AgentStatus.ERROR.value

    def test_required_trust_level_is_verified_external(self):
        assert PreProcessNode.required_trust_level == TrustLevel.VERIFIED_EXTERNAL

    def test_trust_gate_blocks_anonymous(self):
        node = PreProcessNode()
        state = _base_state(
            caller_trust_level=TrustLevel.ANONYMOUS.value,
            user_input=_valid_input(),
        )
        result = node(state)
        assert result["status"] == AgentStatus.ERROR.value

    def test_execute_method_signature(self):
        sig = inspect.signature(PreProcessNode.execute)
        params = list(sig.parameters.keys())
        assert params[1] == "state"
        assert "_invoke_impl" not in PreProcessNode.__dict__
