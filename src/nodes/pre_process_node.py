import json
import re
from typing import Any, ClassVar, cast

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

from src.schemas.state import PublicTenderDocumentComparisonState

_PII_PATTERNS = [
    re.compile(r"\d{4}-\d{4}-\d{4}"),
    re.compile(r"\b\d{12}\b"),
    re.compile(r"機密"),
    re.compile(r"秘密"),
]

_ALLOWED_TYPES = {"pdf", "docx", "json", "txt"}
_MAX_DOCUMENTS = 10
_MAX_INPUT_LENGTH = 1_048_576
_MAX_DOCUMENT_TEXT_LENGTH = 200_000


class PreProcessNode(FunctionNode):
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    def _extra_security_gate_input(
        self, state: PublicTenderDocumentComparisonState
    ) -> PublicTenderDocumentComparisonState:
        raw = state.get("user_input", "")
        for pattern in _PII_PATTERNS:
            if pattern.search(raw):
                state = cast(PublicTenderDocumentComparisonState, dict(state))
                state["status"] = AgentStatus.ERROR.value
                state["error_log"] = ["S-2: PII or classified marker detected in input — rejected"]
                return state
        return state

    def execute(self, state: PublicTenderDocumentComparisonState) -> dict[str, Any]:
        emit_trace_event("tender_input_validation_started", {}, state)
        raw = state.get("user_input", "").strip()
        if not raw:
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["Empty input — tender documents and vendor profile are required"],
            }

        if len(raw) > _MAX_INPUT_LENGTH:
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["Input exceeds the 1 MiB processing limit"],
            }

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["Input must be JSON with 'tender_documents' and 'vendor_profile' keys"],
            }

        if not isinstance(payload, dict):
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["Input JSON must be an object"],
            }

        tender_documents = payload.get("tender_documents", [])
        vendor_profile = payload.get("vendor_profile", {})

        if not isinstance(tender_documents, list) or not tender_documents:
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["'tender_documents' list is empty — at least one document is required"],
            }

        if len(tender_documents) > _MAX_DOCUMENTS:
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": [f"Too many documents: {len(tender_documents)} > max {_MAX_DOCUMENTS}"],
            }

        if not isinstance(vendor_profile, dict) or not vendor_profile:
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["'vendor_profile' is missing or empty"],
            }

        chunks = []
        seen_ids: set[str] = set()
        for doc in tender_documents:
            if not isinstance(doc, dict):
                return {
                    "status": AgentStatus.ERROR.value,
                    "error_log": ["Every tender document must be an object"],
                }
            doc_id = doc.get("id")
            if not isinstance(doc_id, str) or not doc_id.strip() or doc_id in seen_ids:
                return {
                    "status": AgentStatus.ERROR.value,
                    "error_log": ["Each tender document requires a unique non-empty id"],
                }
            seen_ids.add(doc_id)
            raw_type = doc.get("type", "txt")
            if not isinstance(raw_type, str):
                return {
                    "status": AgentStatus.ERROR.value,
                    "error_log": [f"Document {doc_id} type must be a string"],
                }
            doc_type = raw_type.lower()
            if doc_type not in _ALLOWED_TYPES:
                return {
                    "status": AgentStatus.ERROR.value,
                    "error_log": [f"Unsupported document type: {doc_type}. Allowed: {_ALLOWED_TYPES}"],
                }
            text = doc.get("text", "")
            if not isinstance(text, str) or not text.strip() or len(text) > _MAX_DOCUMENT_TEXT_LENGTH:
                return {
                    "status": AgentStatus.ERROR.value,
                    "error_log": [f"Document {doc_id} text must be non-empty and at most 200,000 characters"],
                }
            doc_chunks = _chunk_text(text, chunk_size=500, overlap=50)
            chunks.extend([{"doc_id": doc_id, "chunk": c} for c in doc_chunks])

        vector_index = json.dumps(
            {
                "chunks": chunks,
                "document_count": len(tender_documents),
                "total_chunks": len(chunks),
            }
        )

        validated_input = json.dumps(
            {
                "document_count": len(tender_documents),
                "total_chunks": len(chunks),
                "profile_keys": list(vendor_profile.keys()) if isinstance(vendor_profile, dict) else [],
            }
        )

        emit_trace_event(
            "vector_index_built",
            {"document_count": len(tender_documents), "total_chunks": len(chunks)},
            state,
        )

        return {
            "validated_input": validated_input,
            "vector_index": vector_index,
            "validated_profile": json.dumps(vendor_profile),
            "document_count": len(tender_documents),
            "status": AgentStatus.SUCCESS.value,
        }


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    if not text:
        return []
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += chunk_size - overlap
    return chunks
