"""
agents/data_agent/logger.py
Logs Data Agent decisions to a JSON feedback file (acts as the feedback node).
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

FEEDBACK_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data", "feedback_data_agent.json"
)


def log_decision(event: str, details: dict[str, Any]) -> None:
    """Append a decision record to the feedback log."""
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": "data_agent",
        "event": event,
        **details,
    }
    _append_to_file(record)
    logger.info("[DataAgent Logger] %s | %s", event, details)


def _append_to_file(record: dict[str, Any]) -> None:
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
