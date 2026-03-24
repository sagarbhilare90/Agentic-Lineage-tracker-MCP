"""
agents/graph_agent/poll.py
Decides which graph updates are needed based on Query Agent inferences.
Uses rule-based voting: majority layer across all inferences for a table wins.
"""

import logging
from collections import defaultdict, Counter
from typing import Any

from agents.graph_agent import logger as ga_logger

logger = logging.getLogger(__name__)


def decide_updates(
    inferences: list[dict[str, Any]],
    alias_table: dict[str, str],
) -> list[dict[str, Any]]:
    """
    Returns a list of update dicts:
    {
        "type": "node" | "edge",
        "table": str,            # for node updates
        "layer": str,            # for node updates
        "source": str,           # for edge updates
        "target": str,           # for edge updates
    }
    """
    # ── Resolve aliases ───────────────────────────────────────────────────────
    def resolve(name: str) -> str:
        return alias_table.get(name, name)

    # ── Aggregate layer votes per table ───────────────────────────────────────
    layer_votes: dict[str, list[str]] = defaultdict(list)
    edge_set: set[tuple[str, str]] = set()

    for inf in inferences:
        target = resolve(inf.get("target_table") or "")
        layer  = inf.get("inferred_layer", "unknown")
        if target:
            layer_votes[target].append(layer)
        for src in inf.get("source_tables", []):
            src = resolve(src)
            if src and target and src != target:
                edge_set.add((src, target))

    updates: list[dict[str, Any]] = []

    # Node updates: majority vote
    for table, votes in layer_votes.items():
        counter = Counter(v for v in votes if v != "unknown")
        if counter:
            best_layer = counter.most_common(1)[0][0]
        else:
            best_layer = "unknown"
        updates.append({"type": "node", "table": table, "layer": best_layer})
        ga_logger.log_decision(
            "node_decision",
            {"table": table, "votes": dict(counter), "chosen_layer": best_layer},
        )

    # Edge updates
    for src, tgt in edge_set:
        updates.append({"type": "edge", "source": src, "target": tgt})

    logger.info("[GraphPoll] Decided %d updates (%d node, %d edge).",
                len(updates),
                sum(1 for u in updates if u["type"] == "node"),
                sum(1 for u in updates if u["type"] == "edge"))
    return updates
