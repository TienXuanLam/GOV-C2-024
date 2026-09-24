"""AGENTIC STAR Marketplace entrypoint for GOV-C2-024."""

from pathlib import Path
from typing import Any

from framework.utils.config_loader import load_agent_config
from shared.bootstrap.marketplace_app import run_agent_marketplace

from src.graph.graph import PublicTenderDocumentComparisonAgent

extend_config: dict[str, Any] = {}

if __name__ == "__main__":
    run_agent_marketplace(
        PublicTenderDocumentComparisonAgent,
        agent_name="GOV-C2-024",
        namespace="gov",
        config={**load_agent_config(Path(__file__).resolve().parent), **extend_config},
    )
