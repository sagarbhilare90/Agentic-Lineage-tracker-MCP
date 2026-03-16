# Data Lineage Tracking Agent

An AI-powered agent that analyzes Snowflake query history to automatically classify tables into **Bronze**, **Silver**, and **Gold** medallion layers and maintains a live data lineage graph across the entire pipeline.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Agents](#agents)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [How It Works](#how-it-works)
- [Project Structure](#project-structure)
- [References](#references)

---

## Overview

In a Snowflake medallion architecture, data flows through three stages:

| Layer | Description |
|-------|-------------|
| **Bronze** | Raw, unprocessed data. Schema mirrors the source. May contain missing or incorrect values. |
| **Silver** | Cleaned, filtered, and integrated data in a consistent format for business analytics. |
| **Gold** | Aggregated, curated, single source of truth for business intelligence. |

This agent monitors SQL query history in Snowflake to:
- **Classify** each table into its appropriate medallion layer
- **Map data flow** between tables as a directed acyclic graph (DAG)
- **Maintain a lineage graph** where each table is a node and data relationships are edges

---

## Architecture

### Minimal Architecture

```
Raw Data Source
      |
      v
[Bronze Tables] --> Changelog -->
[Silver Tables] --> Changelog -->  Client MCP Server --> fetch() --> iceDQ Agent
[Gold Tables]   --> Changelog -->
                                          |
                        +-----------------+-----------------+
                        v                 v                 v
                   SQL Query Parser    LLM (Classifier)   Graph API
                   (sqlglot)           (LangChain)        (NetworkX / Neo4j)
                                          |
                                   Graph Visualizer
```

### Multi-Agent Architecture

The system is orchestrated on **LangGraph** with AIOps monitoring on **LangSmith**. Three specialized agents collaborate:

```
Start --> [Data Agent] --> [Query Agent] --> [Graph Agent] --> [BI Node]
               |                |                  |
          iceDQ Node        Feedback           Feedback &
                             Node            Validation Node
```

---

## Agents

### 1. Data Agent (Information Gathering)

Periodically polls the client MCP server (via Snowflake's `QUERY_HISTORY`) to determine when to fetch new query batches. Triggers the Query Agent and logs decisions to a feedback node.

**Tools:**
- `poll.py` - Polls LLM with historical time logs and cost-per-execution data to decide when to fetch
- `trigger.py` - Fetches new query data and notifies the LLM
- `logger.py` - Logs LLM decisions to the feedback node
- `query_agent_activator.py` - Activates the Query Agent

**Optional enhancements:**
- ML-based optimization of fetch timing vs. execution cost
- Seasonal trend detection in query volume

---

### 2. Query Agent (Tool Usage Agent)

Receives raw queries, sanitizes PII/sensitive data, builds a table alias map, and uses an LLM to classify each query's target table as Bronze, Silver, or Gold. Also identifies source and destination tables for lineage edges.

**Tools:**
- `sql_parser.py` - Parses SQL queries into atomic units, removes PII, maintains alias table, triggers LLM
- `logger.py` - Logs LLM classification decisions
- `graph_agent_activator.py` - Triggers the Graph Agent

---

### 3. Graph Agent (Environment Interaction Agent)

Receives classification inferences and alias details from the Query Agent. Decides whether to create new nodes or update existing table categories, then instructs the BI node to apply changes to the lineage graph.

**Tools:**
- `poll.py` - Polls LLM with alias table and inference history to decide on graph updates
- `update_graph.py` - Applies changes to the lineage graph
- `logger.py` - Logs all decisions to feedback node

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Orchestration | [LangGraph](https://www.langchain.com/langgraph) |
| AIOps / Monitoring | [LangSmith](https://www.langchain.com/langsmith) |
| LLM Framework | [LangChain](https://www.langchain.com/) |
| SQL Parsing | [sqlglot](https://github.com/tobymao/sqlglot) |
| Lineage Graph | [NetworkX](https://networkx.org/) / [Neo4j](https://neo4j.com/) |
| Data Source | [Snowflake](https://www.snowflake.com/) (`QUERY_HISTORY`) |
| MCP Server | Custom client MCP server |

---

## Getting Started

### Prerequisites

- Python 3.10+
- Snowflake account with `QUERY_HISTORY` access
- API keys for your chosen LLM provider
- Neo4j instance (or NetworkX for local graph)

### Installation

```bash
git clone https://github.com/your-org/lineage-tracker.git
cd lineage-tracker
pip install -r requirements.txt
```

### Configuration

```bash
cp .env.example .env
# Fill in your Snowflake credentials, LLM API keys, and graph DB connection
```

### Running the Agent

```bash
# Start the full multi-agent pipeline
python main.py

# Or trigger the Data Agent manually for an initial query dump
python agents/data_agent/trigger.py --manual
```

---

## How It Works

1. **Fetch** - The Data Agent pulls unprocessed query logs from Snowflake via the client MCP server.
2. **Parse** - The Query Agent uses `sqlglot` to break query logs into individual SQL statements and strips sensitive data.
3. **Classify** - An LLM analyzes each query's pattern (INSERT, SELECT, MERGE, etc.) and classifies the target table as Bronze, Silver, or Gold.
4. **Decide** - The Graph Agent reviews the classification history and decides whether to update a table's category or add a new node.
5. **Update** - The lineage graph is updated via the Graph API. The BI Node can visualize the graph or revert to a previous version.
6. **Log** - All agent decisions are recorded in feedback nodes for monitoring and analytics.

---

## Project Structure

```
lineage-tracker/
    agents/
        data_agent/
            poll.py
            trigger.py
            logger.py
            query_agent_activator.py
        query_agent/
            sql_parser.py
            logger.py
            graph_agent_activator.py
        graph_agent/
            poll.py
            update_graph.py
            logger.py
    graph/
        lineage_graph.py
    mcp/
        snowflake_mcp_server.py
    config/
        settings.py
    main.py
    requirements.txt
    .env.example
    README.md
```

---

## References

- [SQL Coder by Defog.ai](https://huggingface.co/defog/sqlcoder-7b-2) - SQL generation model
- [CodeQwen Text-to-SQL](https://huggingface.co/Qwen/CodeQwen1.5-7B-Chat) - Code-focused LLM for SQL tasks
- [Snowflake Column-Level Security](https://docs.snowflake.com/en/user-guide/security-column-intro) - Sensitive information masking in Snowflake
- [Snowflake QUERY_HISTORY](https://docs.snowflake.com/en/sql-reference/functions/query_history) - Query history access

---

## License

MIT License. See [LICENSE](LICENSE) for details.
