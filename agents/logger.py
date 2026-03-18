"""
Shared logger utility.
Writes structured JSONL entries to the feedback log file and
also emits to the Python logging system.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict

from config.settings import settings

_log = logging.getLogger(__name__)


def _ensure_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def log_event(agent: str, event_type: str, payload: Dict[str, Any]) -> None:
    """
    Append a structured log entry to the feedback JSONL file.

    Args:
        agent:      Name of the agent emitting the event (e.g. 'data_agent').
        event_type: Short label (e.g. 'fetch_decision', 'classification', 'graph_update').
        payload:    Arbitrary dict of event details.
    """
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "agent": agent,
        "event_type": event_type,
        **payload,
    }

    # Log to Python logger
    _log.info("[%s] %s: %s", agent, event_type, json.dumps(payload))

    # Persist to JSONL feedback file
    try:
        _ensure_dir(settings.FEEDBACK_LOG_PATH)
        with open(settings.FEEDBACK_LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
    except OSError as exc:
        _log.warning("Could not write feedback log: %s", exc)
