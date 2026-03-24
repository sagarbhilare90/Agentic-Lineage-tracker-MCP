"""
agents/graph_agent/graph_agent.py
Graph Agent orchestrator.
Receives query inferences, decides on updates (majority-vote),
applies them to the lineage graph, and persists the result.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from agents.graph_agent.poll import decide_update
from agents.graph_agent.update_graph import apply_inferences
import graph.lineage_graph as _lg_module
from agents.logger import log_event

logger = logging.getLogger(__name__)


def run(inferences: List[Dict[str, Any]]) -> None:
    """
    Full Graph Agent pipeline:
      1. Decide which tables need updating (majority vote).
      2. Apply changes to the lineage graph.
      3. Persist the graph.
      4. Print a human-readable summary.
    """
    logger.info("Graph Agent received %d inferences.", len(inferences))

    # Step 1: resolve final layer per table
    decisions = decide_update(inferences)

    # Step 2: apply to graph
    changes = apply_inferences(decisions)

    # Step 3: persist
    _lg_module.lineage_graph.save()

    log_event(
        agent="graph_agent",
        event_type="run_complete",
        payload={
            "decisions": len(decisions),
            "changes": len(changes),
            "graph_summary": _lg_module.lineage_graph.summary(),
        },
    )

    # Step 4: print summary
    _lg_module.lineage_graph.print_summary()
