# RetailLens

**E-Commerce Analytics Warehouse** | Python · AWS S3 · Snowflake · dbt · Airflow · Streamlit · Docker

[![RetailLens CI](https://github.com/sloanatkins/retaillens/actions/workflows/ci.yml/badge.svg)](https://github.com/sloanatkins/retaillens/actions/workflows/ci.yml)

---

## Overview

RetailLens is an end-to-end ELT analytics pipeline built on the Olist Brazilian E-Commerce dataset — 100,000+ real orders across 9 relational tables. Raw data flows from Kaggle through AWS S3, into Snowflake, and is transformed by dbt into a star schema that powers a Streamlit dashboard answering real business questions.

This is Project 3 of a 4-project data engineering portfolio. The focus here is analytics engineering depth: dimensional modeling, dbt model layers, and SQL that answers questions a business would actually care about.

---

## Architecture

Kaggle API → AWS S3 → Snowflake RAW → dbt (staging → intermediate → mart) → Streamlit

Airflow DAG orchestrates all stages. Plotly powers 3 interactive dashboard views.

**Stack:** Python · AWS S3 · Snowflake · dbt · Apache Airflow (astro-cli) · Streamlit · Plotly · Docker · GitHub Actions

---

## Data Model

Star schema centered on order line items. Grain: one row per order item.

| Table | Rows |
|-------|------|
| fct_order_items | 112,650 |
| dim_customers | 99,441 |
| dim_products | 32,951 |
| dim_dates | 1,461 |
| dim_sellers | 3,095 |

**Denormalization decisions:**
- Product category names are denormalized into dim_products (71-row translation table does not justify a separate dimension)
- Geolocation coordinates are denormalized into dim_customers at the intermediate layer (used in every regional query)

---

## dbt Model Layers

| Layer | Models | Purpose |
|-------|--------|---------|
| Staging (stg_) | 8 models | Clean and rename raw columns, cast types, filter nulls, translate Portuguese category names |
| Intermediate (int_) | 3 models | Join orders to payments and reviews, compute delivery delta, calculate customer CLV and cohort assignment, aggregate seller metrics |
| Mart (fct_, dim_) | 5 models | Final star schema tables queried by the dashboard |

**53 dbt tests passing** across all 16 models: not_null, unique, relationships, accepted_values.

---

## Business Questions Answered

| Question | Model | Insight |
|----------|-------|---------|
| Which product categories drive the most revenue? | fct_order_items + dim_products | Health and beauty leads at R$ 1.2M; bed/bath/table has the highest cancellation rate |
| Which sellers are outliers in delivery speed or review score? | dim_sellers | Avg delivery is 12 days early; outlier sellers with low scores cluster in the late-delivery quadrant |
| How does repeat purchase rate vary by acquisition cohort? | dim_customers | Cohort size peaked in Nov 2017; avg LTV is R$ 155 |
| What is the relationship between freight value and review score? | fct_order_items | Higher freight correlates with lower review scores across most categories |
| Which states generate the most revenue? | dim_customers + fct_order_items | Sao Paulo dominates; regional filtering available in dashboard |

---

## Dashboard

Three interactive views built with Streamlit + Plotly, querying dbt mart tables directly via Snowflake connector.

- **Category Performance** — Revenue by category with cancellation rate overlay. Sidebar filter for minimum order volume.
- **Seller Scorecard** — Scatter plot of review score vs delivery delta, sized by order volume. Filter by state and minimum orders.
- **Customer Cohorts** — Cohort size over time, repeat purchase rate trend, and average LTV by acquisition month.

---

## Pipeline

The Airflow DAG runs daily at 06:00 UTC with 8 sequential tasks and retries=2 on each:

download_raw → upload_to_s3 → validate_data → load_to_snowflake → dbt_staging → dbt_intermediate → dbt_mart → dbt_test

The validation task runs 30 pre-load checks across all 9 source tables before anything touches Snowflake.

---

## Project Structureretaillens/

├── ingestion/

│   ├── download.py          # Kaggle download with checksum verification

│   ├── upload_s3.py         # S3 upload with date partitioning

│   ├── validate.py          # 30 pre-load validation checks

│   └── load_snowflake.py    # COPY INTO all 9 RAW tables

├── retaillens_dbt/

│   └── models/

│       ├── staging/         # 8 stg_ models

│       ├── intermediate/    # 3 int_ models

│       └── mart/            # 5 fct_/dim_ models

├── dashboard/

│   ├── app.py               # Streamlit entry point

│   ├── connection.py        # Snowflake connector

│   └── views/               # One file per dashboard view

├── dags/

│   └── retaillens_dag.py    # Airflow DAG

├── docs/

│   ├── RetailLens_Proposal_v1.docx

│   └── RetailLens_ADD_v1.docx

├── Dockerfile

├── docker-compose.yml

└── requirements.txt---

## Running Locally

Prerequisites: Python 3.11+, Docker Desktop, astro-cli, Snowflake account, AWS account

```bash
git clone https://github.com/sloanatkins/retaillens
cd retaillens
cp .env.example .env
python ingestion/download.py
python ingestion/upload_s3.py
python ingestion/validate.py
python ingestion/load_snowflake.py
cd retaillens_dbt && dbt run && dbt test
cd .. && streamlit run dashboard/app.py
```

Or run everything with Docker:

```bash
docker-compose up
```

---

## Key Technical Decisions

**ELT over ETL:** Raw data lands in S3 and Snowflake unchanged. All transformation happens inside the warehouse with dbt. If transform logic changes, rerun dbt — no re-ingestion needed.

**Star schema grain at order item level:** Graining at the order level would lose the ability to analyze revenue and review scores at the product level without re-aggregating.

**Postgres-first development:** The full dbt model hierarchy was developed and tested against local Postgres before migrating to Snowflake, keeping the feedback loop fast during active development.

**RSA key-pair auth for Snowflake:** Snowflake trial accounts enforce MFA account-wide. Key-pair authentication bypasses this for programmatic access — the production-standard approach anyway.

---

*Sloan M. Atkins · University of Miami · CS + Mathematics, Class of 2027*
*Data Engineering Portfolio · Project 3 of 4*
