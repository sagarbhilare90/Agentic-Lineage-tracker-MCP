"""
agents/graph_agent/update_graph.py
Applies a list of update dicts to the LineageGraph singleton.
"""

import logging
from typing import Any

from graph.lineage_graph import get_graph
from agents.graph_agent import logger as ga_logger

logger = logging.getLogger(__name__)


def apply_updates(updates: list[dict[str, Any]]) -> None:
    """Apply node and edge updates to the lineage graph."""
    graph = get_graph()
    nodes_added = nodes_changed = edges_added = 0

    for upd in updates:
        if upd["type"] == "node":
            changed = graph.add_or_update_node(upd["table"], upd["layer"])
            if changed:
                existing = graph.get_node(upd["table"])
                if existing and existing.get("layer") == upd["layer"]:
                    nodes_added += 1
                else:
                    nodes_changed += 1

        elif upd["type"] == "edge":
            added = graph.add_edge(upd["source"], upd["target"])
            if added:
                edges_added += 1

    summary = graph.summary()
    ga_logger.log_decision(
        "graph_updated",
        {
            "nodes_added": nodes_added,
            "nodes_changed": nodes_changed,
            "edges_added": edges_added,
            "graph_summary": summary,
        },
    )
    logger.info(
        "[UpdateGraph] nodes_added=%d changed=%d edges_added=%d | graph=%s",
        nodes_added, nodes_changed, edges_added, summary,
    )
