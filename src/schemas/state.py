"""Flat, checkpoint-safe state for GOV-C2-024."""

from typing import Optional

from framework.schemas.agent_state import AgentState


class PublicTenderDocumentComparisonState(AgentState):
    validated_input: Optional[str]
    vector_index: Optional[str]
    validated_profile: Optional[str]
    document_count: Optional[int]
    requirements_list: Optional[str]
    coverage_scores: Optional[str]
    gap_list: Optional[str]
    mandatory_review_flags: Optional[str]
