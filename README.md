# Agentic-Lineage-tracker-MCP

Lineage Tracking Agent

An AI-powered data lineage tracking system that analyzes SQL queries from a Snowflake database and automatically builds a lineage graph across Bronze → Silver → Gold layers in a medallion architecture.

The agent classifies tables, detects relationships between them, and continuously updates a lineage graph for monitoring and analytics.

Project Reference: 

Lineage_tracker

Overview

Modern data pipelines often follow the Medallion Architecture:

Bronze Layer → Raw ingested data

Silver Layer → Cleaned and transformed data

Gold Layer → Aggregated business-ready data

This project builds an AI Agent that automatically identifies these layers and tracks data movement between tables by analyzing SQL query logs.

The output is a data lineage graph where:

Each table = node

Each data flow = edge

This helps data engineers understand how data moves across the system.

Key Features

Automated SQL query analysis

AI-based table classification

Data lineage graph generation

Snowflake query history integration

Multi-agent architecture for scalability

Graph visualization support

PII masking before LLM processing

Real-time lineage updates

Architecture

The system consists of multiple agents responsible for different tasks:

Data Agent

Responsible for collecting query history from Snowflake.

Functions:

Poll query logs

Trigger query processing

Detect high-volume query periods

Send logs to Query Agent

Query Agent

Responsible for query analysis and classification.

Functions:

SQL parsing

Alias resolution

PII masking

Table classification using LLM

Source → Target table detection

Graph Agent

Responsible for maintaining the lineage graph.

Functions:

Create graph nodes for tables

Create edges for table dependencies

Update table categories

Maintain graph state

System Workflow

Query history is fetched from Snowflake using QUERY_HISTORY API.

Queries are cleaned and parsed.

Sensitive information is removed.

Queries are sent to an LLM for classification.

The LLM determines:

Table category (Bronze/Silver/Gold)

Source tables

Target tables

Graph Agent updates the lineage graph.

Graph can be visualized via a Graph API or BI tools.

The workflow illustrated in the architecture diagram (page 3 of the document) shows agents orchestrated through LangGraph and LangSmith monitoring. 

Lineage_tracker

Table Classification Logic

The system uses query behavior to infer table layers.

Bronze Tables

Raw ingestion

Unstructured or incomplete data

Heavy transformation queries

Example patterns:

INSERT INTO bronze_table
SELECT * FROM raw_source
Silver Tables

Cleaned and structured datasets

Data integrated from multiple sources

Example patterns:

INSERT INTO silver_table
SELECT cleaned_data FROM bronze_table
Gold Tables

Aggregated datasets

Business reporting tables

Analytical queries

Example patterns:

SELECT SUM(sales) FROM silver_table
GROUP BY region
Technology Stack
Component	Technology
LLM	OpenAI / SQLCoder / CodeQwen
Orchestration	LangGraph
Monitoring	LangSmith
SQL Parsing	SQLGlot
Graph Database	Neo4j / NetworkX
Data Source	Snowflake
Backend	Python
Visualization	Graph UI / BI Tools
Project Structure
lineage-tracking-agent/
│
├── agents/
│   ├── data_agent.py
│   ├── query_agent.py
│   └── graph_agent.py
│
├── parsers/
│   └── sql_parser.py
│
├── graph/
│   ├── update_graph.py
│   └── graph_schema.py
│
├── utils/
│   ├── logger.py
│   └── pii_masking.py
│
├── config/
│   └── config.yaml
│
├── main.py
└── README.md
Example Lineage Graph

Example lineage flow:

Raw_Source
     │
     ▼
Bronze_Table
     │
     ▼
Silver_Table
     │
     ▼
Gold_Table

Graph Representation:

Raw_Source → Bronze → Silver → Gold
Installation

Clone the repository

git clone https://github.com/yourusername/lineage-tracking-agent.git

Navigate to project directory

cd lineage-tracking-agent

Install dependencies

pip install -r requirements.txt
Configuration

Set the following environment variables:

SNOWFLAKE_ACCOUNT=
SNOWFLAKE_USER=
SNOWFLAKE_PASSWORD=
SNOWFLAKE_DATABASE=

OPENAI_API_KEY=
Running the Agent

Start the lineage agent

python main.py

The system will:

Fetch query logs

Classify tables

Update lineage graph

Future Improvements

ML-based query pattern classification

Streaming query ingestion

Real-time lineage monitoring

Integration with Airflow / dbt

Automated anomaly detection

Graph-based lineage search

Potential Models

SQLCoder (Defog)

CodeQwen Text-to-SQL

These models can improve SQL understanding and query classification. 

Lineage_tracker

Use Cases

Data warehouse governance

ETL pipeline debugging

Data impact analysis

Compliance and auditing

Data catalog automation



That would make the repo look like a serious AI/ML engineering project.

Sources
