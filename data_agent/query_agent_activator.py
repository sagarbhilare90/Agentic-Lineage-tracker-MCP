"""
agents/data_agent/query_agent_activator.py
Activates the Query Agent by passing fetched rows to it.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def activate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Hand query rows to the Query Agent pipeline and return inferences.
    Importing here to avoid circular imports at module load time.
    """
    from agents.query_agent.sql_parser import process_queries

    logger.info("[DataAgent] Activating Query Agent with %d rows.", len(rows))
    inferences = process_queries(rows)
    return inferences
