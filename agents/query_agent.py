"""
agents/query_agent/query_agent.py
Classifies each table into Bronze / Silver / Gold by sending
cleaned, PII-masked queries to an LLM.

In DEMO_MODE the LLM call is skipped and a rule-based classifier is
used instead, so the full pipeline works without any API keys.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from config.settings import settings
from agents.query_agent.sql_parser import parse_batch, ParsedQuery
from agents.logger import log_event

logger = logging.getLogger(__name__)

# Canonical layer labels
LAYERS = {"BRONZE", "SILVER", "GOLD"}

# ── Classification prompt ──────────────────────────────────────────────────

_SYSTEM_PROMPT = """
You are a data-engineering expert specialised in Snowflake medallion architectures.

Given a SQL query, determine:
1. The LAYER of the TARGET table: BRONZE, SILVER, or GOLD.
2. The TARGET table name (the table being written to, if any).
3. The SOURCE table names (tables being read from).

Definitions:
- BRONZE : Raw ingestion layer. Tables receive data directly from external sources.
           Queries are mostly plain INSERT/COPY with no transformation logic.
           The table may contain missing or inconsistent values.
- SILVER : Cleansing and integration layer. Tables are populated via
           INSERT ... SELECT with filtering, TRIM, type-casting, JOINs across
           multiple sources, or deduplication logic.
- GOLD   : Business-ready aggregation layer. Tables are updated via MERGE or
           INSERT ... SELECT with GROUP BY / aggregation functions.
           Queries affect small, pre-defined result sets targeted at BI tools.

Respond ONLY with valid JSON in this exact format:
{
  "layer": "BRONZE" | "SILVER" | "GOLD",
  "target_table": "<table name or null>",
  "source_tables": ["<table1>", "<table2>"],
  "reasoning": "<one sentence>"
}
""".strip()


# ── Rule-based fallback (no LLM needed) ───────────────────────────────────

def _rule_based_classify(pq: ParsedQuery) -> Dict[str, Any]:
    """
    Heuristic classifier used in DEMO_MODE or when the LLM is unavailable.
    """
    sql_upper = pq.clean_sql.upper()
    schema = (pq.schema_hint or "").upper()

    # Schema name gives a strong hint
    if schema in LAYERS:
        layer = schema
    # MERGE with GROUP BY -> Gold
    elif pq.query_type == "MERGE":
        layer = "GOLD"
    # SELECT only -> assume the table belongs to the schema of the query
    elif pq.query_type == "SELECT":
        layer = schema if schema in LAYERS else "SILVER"
    # INSERT with JOIN / type casting -> Silver
    elif pq.query_type in ("INSERT", "CREATE") and (
        "JOIN" in sql_upper or "TRIM(" in sql_upper
        or "TRY_TO_DATE" in sql_upper or "LOWER(" in sql_upper
    ):
        layer = "SILVER"
    # Plain INSERT without transformation -> Bronze
    elif pq.query_type == "INSERT":
        layer = "BRONZE"
    # UPDATE -> Bronze (data correction on raw tables)
    elif pq.query_type == "UPDATE":
        layer = "BRONZE"
    else:
        layer = "SILVER"

    return {
        "layer": layer,
        "target_table": pq.target_table,
        "source_tables": pq.source_tables,
        "reasoning": f"Rule-based classification (query_type={pq.query_type}, schema={schema})",
    }


# ── LLM-based classifier ───────────────────────────────────────────────────

def _llm_classify(pq: ParsedQuery) -> Dict[str, Any]:
    """Call the configured LLM to classify a single parsed query."""
    try:
        if settings.LLM_PROVIDER == "openai":
            return _classify_openai(pq)
        elif settings.LLM_PROVIDER == "anthropic":
            return _classify_anthropic(pq)
        else:
            logger.warning("Unknown LLM_PROVIDER '%s'. Falling back to rules.", settings.LLM_PROVIDER)
            return _rule_based_classify(pq)
    except Exception as exc:
        logger.error("LLM classification failed for %s: %s. Using rules.", pq.query_id, exc)
        return _rule_based_classify(pq)


def _classify_openai(pq: ParsedQuery) -> Dict[str, Any]:
    from openai import OpenAI  # type: ignore

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": pq.clean_sql},
        ],
        temperature=0,
    )
    return _parse_llm_response(response.choices[0].message.content)


def _classify_anthropic(pq: ParsedQuery) -> Dict[str, Any]:
    import anthropic  # type: ignore

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=256,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": pq.clean_sql}],
    )
    return _parse_llm_response(message.content[0].text)


def _parse_llm_response(text: str) -> Dict[str, Any]:
    """Extract JSON from LLM response text."""
    # Strip markdown code fences if present
    text = re.sub(r"```(?:json)?", "", text).strip()
    data = json.loads(text)
    layer = data.get("layer", "SILVER").upper()
    if layer not in LAYERS:
        layer = "SILVER"
    return {
        "layer": layer,
        "target_table": data.get("target_table"),
        "source_tables": data.get("source_tables", []),
        "reasoning": data.get("reasoning", ""),
    }


# ── Main entry point ───────────────────────────────────────────────────────

def run(raw_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Full Query Agent pipeline:
      1. Parse + PII-mask all queries.
      2. Classify each query.
      3. Log results.
      4. Return inference list for the Graph Agent.
    """
    parsed = parse_batch(raw_rows)
    results = []

    for pq in parsed:
        if settings.DEMO_MODE:
            classification = _rule_based_classify(pq)
        else:
            classification = _llm_classify(pq)

        result = {
            "query_id": pq.query_id,
            "query_type": pq.query_type,
            "clean_sql": pq.clean_sql,
            "layer": classification["layer"],
            "target_table": classification["target_table"] or pq.target_table,
            "source_tables": classification["source_tables"] or pq.source_tables,
            "reasoning": classification["reasoning"],
        }
        results.append(result)

        log_event(
            agent="query_agent",
            event_type="classification",
            payload={
                "query_id": pq.query_id,
                "target_table": result["target_table"],
                "layer": result["layer"],
                "source_tables": result["source_tables"],
            },
        )

    logger.info(
        "Query Agent classified %d queries  |  Bronze=%d  Silver=%d  Gold=%d",
        len(results),
        sum(1 for r in results if r["layer"] == "BRONZE"),
        sum(1 for r in results if r["layer"] == "SILVER"),
        sum(1 for r in results if r["layer"] == "GOLD"),
    )

    return results
