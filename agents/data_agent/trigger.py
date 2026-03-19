"""
agents/data_agent/trigger.py
Executes the actual fetch from the MCP server and hands results downstream.
Can be called programmatically or via CLI:  python agents/data_agent/trigger.py --manual
"""

import argparse
import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from config.settings import FETCH_BATCH_SIZE
from mcp.snowflake_mcp_server import SnowflakeMCPServer
from agents.data_agent import logger as da_logger

logger = logging.getLogger(__name__)


def fetch_queries(mcp: SnowflakeMCPServer) -> list[dict]:
    """Fetch a batch of queries and log the outcome."""
    rows = mcp.fetch_queries(batch_size=FETCH_BATCH_SIZE)
    da_logger.log_decision("fetch_complete", {"rows_fetched": len(rows)})
    logger.info("[Trigger] Fetched %d query rows.", len(rows))
    return rows


# ── CLI entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import logging as _logging
    _logging.basicConfig(level="INFO", format="%(levelname)s | %(message)s")

    parser = argparse.ArgumentParser(description="Manually trigger a query fetch.")
    parser.add_argument("--manual", action="store_true", help="Force a fetch regardless of poll result.")
    args = parser.parse_args()

    mcp = SnowflakeMCPServer()
    rows = fetch_queries(mcp)
    print(f"Fetched {len(rows)} rows.")
    for r in rows[:3]:
        print(" ", r.get("query_id"), "|", r.get("query_text", "")[:80])
