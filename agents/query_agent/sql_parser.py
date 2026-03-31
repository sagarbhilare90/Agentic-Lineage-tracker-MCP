"""
agents/query_agent/sql_parser.py

1. Parses each raw SQL string into structured metadata using sqlglot.
2. Masks PII / sensitive column names before anything is sent to an LLM.
3. Maintains an in-memory alias table (table alias -> canonical name).
4. Classifies each query (Bronze / Silver / Gold) via rule-based heuristics
   AND optionally via an LLM call (enabled when ANTHROPIC_API_KEY is set).
5. Returns a list of inference dicts for the Graph Agent.
"""

import logging
import re
from typing import Any

import sqlglot
import sqlglot.expressions as exp

from config.settings import ANTHROPIC_API_KEY
from agents.query_agent import logger as qa_logger

logger = logging.getLogger(__name__)

# Columns that should be masked before sending to an LLM
PII_PATTERNS = re.compile(
    r"\b(email|phone|ssn|password|credit_card|dob|date_of_birth|ip_address|address)\b",
    re.IGNORECASE,
)

# Alias table: maps alias -> canonical table name (shared across the session)
_alias_table: dict[str, str] = {}


def process_queries(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Main entry point. Returns a list of inference dicts:
    {
        query_id, source_tables, target_table,
        inferred_layer, confidence, masked_query
    }
    """
    inferences = []
    for row in rows:
        try:
            result = _process_single(row)
            if result:
                inferences.append(result)
        except Exception as exc:
            logger.warning("[SQLParser] Skipping query %s: %s", row.get("query_id"), exc)
    return inferences


def get_alias_table() -> dict[str, str]:
    return dict(_alias_table)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _process_single(row: dict[str, Any]) -> dict[str, Any] | None:
    raw_sql = row.get("query_text", "").strip()
    if not raw_sql:
        return None

    masked_sql = _mask_pii(raw_sql)
    parsed = _parse_sql(masked_sql)
    if parsed is None:
        return None

    source_tables = _extract_source_tables(parsed)
    target_table  = _extract_target_table(parsed)
    _update_alias_table(parsed)

    layer, confidence = _classify(raw_sql, target_table, source_tables)

    result = {
        "query_id":      row.get("query_id", "unknown"),
        "source_tables": source_tables,
        "target_table":  target_table,
        "inferred_layer": layer,
        "confidence":    confidence,
        "masked_query":  masked_sql,
        "rows_produced": row.get("rows_produced", 0),
    }
    qa_logger.log_decision("query_classified", result)
    return result


def _mask_pii(sql: str) -> str:
    return PII_PATTERNS.sub("<MASKED>", sql)


def _parse_sql(sql: str):
    try:
        statements = sqlglot.parse(sql, error_level=sqlglot.ErrorLevel.WARN)
        return statements[0] if statements else None
    except Exception:
        return None


def _extract_source_tables(stmt) -> list[str]:
    sources = []
    for table in stmt.find_all(exp.Table):
        name = _full_table_name(table)
        if name:
            sources.append(name)
    return list(dict.fromkeys(sources))  # deduplicate preserving order


def _extract_target_table(stmt) -> str | None:
    # INSERT INTO / MERGE INTO / UPDATE / CREATE TABLE AS
    for node_type in (exp.Insert, exp.Merge, exp.Update, exp.Create):
        node = stmt.find(node_type)
        if node:
            tbl = node.find(exp.Table)
            if tbl:
                return _full_table_name(tbl)
    return None


def _full_table_name(table_node) -> str | None:
    db    = table_node.args.get("db")
    tbl   = table_node.args.get("this")
    alias = table_node.args.get("alias")
    if tbl is None:
        return None
    name = f"{db}.{tbl}" if db else str(tbl)
    if alias:
        _alias_table[str(alias)] = name
    return name


def _update_alias_table(stmt) -> None:
    for alias_node in stmt.find_all(exp.TableAlias):
        canonical = alias_node.parent
        if canonical:
            tbl = canonical.find(exp.Table)
            if tbl:
                _alias_table[str(alias_node.name)] = _full_table_name(tbl) or str(alias_node.name)


def _classify(sql: str, target: str | None, sources: list[str]) -> tuple[str, str]:
    """
    Rule-based classification. Returns (layer, confidence).
    Falls back to LLM classification when an API key is available.
    """
    sql_upper = sql.upper()
    target_lower = (target or "").lower()

    # ── Schema-name hint ─────────────────────────────────────────────────────
    if "gold." in target_lower:
        return "gold", "high"
    if "silver." in target_lower:
        return "silver", "high"
    if "bronze." in target_lower or "raw_" in target_lower:
        return "bronze", "high"

    # ── Query-pattern heuristics ─────────────────────────────────────────────
    has_aggregation = any(kw in sql_upper for kw in ("SUM(", "COUNT(", "AVG(", "GROUP BY"))
    has_join        = "JOIN" in sql_upper
    has_insert      = sql_upper.startswith("INSERT")
    has_update      = sql_upper.startswith("UPDATE") or sql_upper.startswith("MERGE")
    has_cleaning    = any(kw in sql_upper for kw in ("TRIM(", "LOWER(", "UPPER(", "REGEXP", "WHERE"))
    is_select_only  = sql_upper.startswith("SELECT")

    # Gold: aggregation / BI reads
    if has_aggregation and has_insert:
        return "gold", "medium"
    if is_select_only and not has_insert:
        # bare SELECT from something that looks like gold
        if any("gold" in s.lower() or "summary" in s.lower() or "performance" in s.lower() for s in sources):
            return "gold", "medium"

    # Silver: cleaning / joining / structured loading
    if (has_cleaning or has_join) and has_insert:
        return "silver", "medium"
    if has_update and any("silver" in s.lower() for s in sources):
        return "silver", "medium"

    # Bronze: raw ingestion or direct mutations on raw tables
    if has_insert and not has_join and not has_cleaning:
        return "bronze", "medium"
    if has_update:
        return "bronze", "medium"

    # ── Optional LLM fallback ─────────────────────────────────────────────────
    if ANTHROPIC_API_KEY:
        return _llm_classify(sql)

    return "unknown", "low"


def _llm_classify(sql: str) -> tuple[str, str]:
    """
    Ask an LLM to classify the table stage.
    Only called when ANTHROPIC_API_KEY is set in .env.
    """
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=64,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "You are a data engineer. Classify the TARGET table of the following SQL "
                        "as Bronze, Silver, or Gold based on the Medallion architecture. "
                        "Reply with exactly one word: Bronze, Silver, or Gold.\n\n"
                        f"SQL:\n{sql[:800]}"
                    ),
                }
            ],
        )
        word = message.content[0].text.strip().capitalize()
        if word in ("Bronze", "Silver", "Gold"):
            return word.lower(), "llm"
    except Exception as exc:
        logger.warning("[SQLParser] LLM classify failed: %s", exc)
    return "unknown", "low"
