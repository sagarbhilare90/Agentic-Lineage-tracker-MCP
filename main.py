"""
main.py
Orchestrates the full Data Lineage Tracking Agent pipeline.

Run:
    python main.py              # single pass (demo mode by default)
    python main.py --loop       # continuous polling loop
    python main.py --reset      # clear graph + feedback logs, then run once
    python main.py --visualize  # run pipeline then open graph visualisation
"""

import argparse
import json
import logging
import os
import sys
import time

from config.settings import DEMO_MODE, POLL_INTERVAL_SECONDS, LOG_LEVEL

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


def run_pipeline() -> None:
    """Execute one full pass: fetch -> parse -> classify -> update graph."""
    from mcp.snowflake_mcp_server import SnowflakeMCPServer
    from agents.data_agent.poll import should_fetch
    from agents.data_agent.trigger import fetch_queries
    from agents.data_agent.query_agent_activator import activate as activate_query_agent
    from agents.query_agent.sql_parser import get_alias_table
    from agents.query_agent.graph_agent_activator import activate as activate_graph_agent
    from graph.lineage_graph import get_graph

    mcp = SnowflakeMCPServer()

    # Step 1 – Poll
    fetch, poll_ctx = should_fetch(mcp)
    if not fetch:
        logger.info("Poll says SKIP. Nothing to do.")
        return

    # Step 2 – Fetch
    rows = fetch_queries(mcp)
    if not rows:
        logger.info("No rows returned. Exiting pipeline.")
        return

    # Step 3 – Query Agent (parse + classify)
    inferences = activate_query_agent(rows)
    logger.info("Query Agent produced %d inferences.", len(inferences))

    # Step 4 – Graph Agent (update lineage graph)
    alias_table = get_alias_table()
    activate_graph_agent(inferences, alias_table)

    # Step 5 – Print summary
    graph = get_graph()
    summary = graph.summary()
    print("\n" + "=" * 60)
    print("  LINEAGE GRAPH SUMMARY")
    print("=" * 60)
    print(f"  Total nodes : {summary['total_nodes']}")
    print(f"  Total edges : {summary['total_edges']}")
    print(f"  By layer    : {summary['layers']}")
    print("=" * 60)
    print("\n  NODES:")
    for node in sorted(graph.nodes(), key=lambda n: (n.get("layer",""), n["name"])):
        print(f"    [{node.get('layer','?').upper():6}]  {node['name']}")
    print("\n  EDGES (data flow):")
    for edge in graph.edges():
        print(f"    {edge['source']}  -->  {edge['target']}")
    print()


def reset_state() -> None:
    """Remove all generated data files so the demo starts fresh."""
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    files_to_remove = [
        "feedback_data_agent.json",
        "feedback_query_agent.json",
        "feedback_graph_agent.json",
        "lineage_graph_snapshot.json",
    ]
    for fname in files_to_remove:
        path = os.path.join(data_dir, fname)
        if os.path.exists(path):
            os.remove(path)
            logger.info("Removed %s", path)

    # Also reset the MCP demo cursor via a fresh instance
    from mcp.snowflake_mcp_server import SnowflakeMCPServer
    SnowflakeMCPServer().reset_cursor()

    # Reset graph singleton
    import graph.lineage_graph as lg
    lg._graph_instance = None
    logger.info("State reset complete.")


def visualize() -> None:
    """Print the graph as a simple ASCII adjacency list."""
    from graph.lineage_graph import get_graph
    graph = get_graph()
    data = graph.export_json()
    print("\nGraph JSON export saved to data/lineage_graph_snapshot.json")
    print(json.dumps(data["summary"], indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Data Lineage Tracking Agent")
    parser.add_argument("--loop", action="store_true", help="Run in continuous polling loop")
    parser.add_argument("--reset", action="store_true", help="Clear state before running")
    parser.add_argument("--visualize", action="store_true", help="Show graph summary after run")
    args = parser.parse_args()

    mode = "DEMO" if DEMO_MODE else "LIVE"
    logger.info("Starting Lineage Tracker | mode=%s", mode)

    if args.reset:
        reset_state()

    if args.loop:
        logger.info("Entering polling loop (interval=%ds). Press Ctrl+C to stop.", POLL_INTERVAL_SECONDS)
        while True:
            try:
                run_pipeline()
            except KeyboardInterrupt:
                logger.info("Stopped by user.")
                break
            except Exception as exc:
                logger.error("Pipeline error: %s", exc, exc_info=True)
            time.sleep(POLL_INTERVAL_SECONDS)
    else:
        run_pipeline()

    if args.visualize:
        visualize()
