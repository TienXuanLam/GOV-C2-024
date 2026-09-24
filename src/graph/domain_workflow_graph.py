"""Inner requirement extraction and evidence coverage workflow."""

from typing import Any

from langgraph.graph import END, START
from framework.graph.base_graph import BaseGraph
from framework.schemas.agent_state import AgentState
from framework.schemas.agent_status import AgentStatus
from src.nodes.requirement_extraction_node import RequirementExtractionNode
from src.nodes.vendor_coverage_node import VendorCoverageNode
from src.schemas.state import PublicTenderDocumentComparisonState


class TenderComparisonWorkflowGraph(BaseGraph):
    @property
    def name(self) -> str:
        return "public_tender_comparison_workflow"

    @property
    def state_schema(self) -> type:
        return PublicTenderDocumentComparisonState

    def _validate_config(self) -> None:
        return None

    def register_nodes(self) -> None:
        self._nodes["requirement_extraction"] = RequirementExtractionNode()
        self._nodes["vendor_coverage"] = VendorCoverageNode()

    def add_edges(self) -> None:
        self._sg.add_edge(START, "requirement_extraction")
        self._sg.add_conditional_edges("requirement_extraction", self.route)
        self._sg.add_edge("vendor_coverage", END)

    def route(self, state: AgentState) -> str:
        return END if state.get("status") == AgentStatus.ERROR.value else "vendor_coverage"

    def get_output(self, state: AgentState) -> dict[str, Any]:
        fields = ("requirements_list", "coverage_scores", "gap_list", "mandatory_review_flags")
        return {
            "output": {field: state.get(field) for field in fields},
            "status": state.get("status", AgentStatus.ERROR.value),
            "trace_id": state.get("trace_id"),
            "correlation_id": state.get("correlation_id"),
            "node_history": state.get("node_history", []),
        }
