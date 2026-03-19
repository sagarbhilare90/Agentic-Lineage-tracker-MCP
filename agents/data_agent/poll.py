"""
agents/data_agent/poll.py
Polls the MCP server to decide whether it is time to fetch a new batch.
Uses simple heuristics (configurable threshold) so the project runs without
an LLM key; swap in an LLM call via the commented block when ready.
"""

import logging
from typing import Any

from config.settings import FETCH_BATCH_SIZE
from mcp.snowflake_mcp_server import SnowflakeMCPServer
from agents.data_agent import logger as da_logger

logger = logging.getLogger(__name__)

FETCH_THRESHOLD = 1  # trigger fetch when at least this many queries are waiting


def should_fetch(mcp: SnowflakeMCPServer) -> tuple[bool, dict[str, Any]]:
    """
    Determine whether a fetch should be triggered.

    Returns:
        (should_fetch: bool, context: dict)  – context is forwarded to trigger.py
    """
    count = mcp.get_unprocessed_query_count()

    # --- Optional: replace the block below with an LLM-based decision ---------
    # from langchain_anthropic import ChatAnthropic
    # llm = ChatAnthropic(model="claude-3-haiku-20240307")
    # decision = llm.invoke(f"There are {count} unprocessed queries. Should we fetch now? Reply YES or NO.")
    # fetch = "YES" in decision.content.upper()
    # --------------------------------------------------------------------------

    fetch = count >= FETCH_THRESHOLD
    context = {
        "unprocessed_count": count,
        "fetch_threshold": FETCH_THRESHOLD,
        "decision": "FETCH" if fetch else "SKIP",
    }
    da_logger.log_decision("poll_result", context)
    logger.info("[Poll] %s (unprocessed=%d)", context["decision"], count)
    return fetch, context
