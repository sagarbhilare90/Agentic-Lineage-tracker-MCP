"""
agents/query_agent/graph_agent_activator.py
Passes Query Agent inferences to the Graph Agent.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def activate(inferences: list[dict[str, Any]], alias_table: dict[str, str]) -> None:
    from agents.graph_agent.poll import decide_updates
    from agents.graph_agent.update_graph import apply_updates
    from agents.graph_agent import logger as ga_logger

    logger.info("[QueryAgent] Activating Graph Agent with %d inferences.", len(inferences))
    updates = decide_updates(inferences, alias_table)
    apply_updates(updates)
    ga_logger.log_decision("graph_agent_activated", {"update_count": len(updates)})
