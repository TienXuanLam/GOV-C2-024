"""Outer Cat 2 graph for public tender document comparison."""

import json
from typing import TYPE_CHECKING, Any, ClassVar

from framework.graph.agent_base_graph import AgentBaseGraph
from framework.nodes.graph_node import GraphNode
from framework.schemas.agent_state import AgentState
from framework.schemas.trust_level import TrustLevel
from src.nodes.post_process_node import PostProcessNode
from src.nodes.pre_process_node import PreProcessNode
from src.schemas.state import PublicTenderDocumentComparisonState

if TYPE_CHECKING:
    from src.graph.domain_workflow_graph import TenderComparisonWorkflowGraph


class TenderComparisonWorkflowGraphNode(GraphNode):
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL
    error_strategy: ClassVar[str] = "propagate"
    propagate_hitl: ClassVar[bool] = False

    def get_subgraph(self) -> "TenderComparisonWorkflowGraph":
        from src.graph.domain_workflow_graph import TenderComparisonWorkflowGraph

        return TenderComparisonWorkflowGraph()

    def extract_input(self, state: AgentState) -> str:
        return json.dumps(
            {
                "vector_index": state.get("vector_index"),
                "validated_profile": state.get("validated_profile"),
            }
        )

    def merge_output(self, state: AgentState, sub_result: dict[str, Any]) -> dict[str, Any]:
        output = sub_result.get("output", {}) or {}
        if not isinstance(output, dict):
            output = {}
        return {**output, "status": sub_result.get("status")}


class PublicTenderDocumentComparisonAgent(AgentBaseGraph):
    @property
    def name(self) -> str:
        return "PublicTenderDocumentComparisonAgent"

    @property
    def state_schema(self) -> type:
        return PublicTenderDocumentComparisonState

    def register_nodes(self) -> None:
        super().register_nodes()
        self._nodes["pre_process"] = PreProcessNode()
        self._nodes["main"] = TenderComparisonWorkflowGraphNode()
        self._nodes["post_process"] = PostProcessNode()
