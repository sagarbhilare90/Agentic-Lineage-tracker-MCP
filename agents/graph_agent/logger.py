"""
agents/graph_agent/logger.py
Logs Graph Agent decisions to a JSON feedback file.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

FEEDBACK_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data", "feedback_graph_agent.json"
)


def log_decision(event: str, details: dict[str, Any]) -> None:
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": "graph_agent",
        "event": event,
        **details,
    }
    _append(record)
    logger.debug("[GraphAgent Logger] %s", event)


def _append(record: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(FEEDBACK_FILE), exist_ok=True)
    existing: list = []
    if os.path.exists(FEEDBACK_FILE):
        with open(FEEDBACK_FILE, "r") as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                existing = []
    existing.append(record)
    with open(FEEDBACK_FILE, "w") as f:
        json.dump(existing, f, indent=2, default=str)
