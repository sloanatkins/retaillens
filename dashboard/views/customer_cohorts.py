import streamlit as st
import plotly.express as px
import pandas as pd
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from connection import run_query

def render():
    st.title("Customer Cohort Analysis")
    st.markdown("How does repeat purchase rate vary by customer acquisition month?")

    with st.spinner("Loading cohort data..."):
        df = run_query("""
            SELECT
                DATE_TRUNC('month', COHORT_MONTH) as cohort_month,
                COUNT(DISTINCT CUSTOMER_ID) as cohort_size,
                AVG(TOTAL_ORDERS) as avg_orders,
                AVG(LIFETIME_VALUE) as avg_ltv,
                AVG(AVG_REVIEW_SCORE) as avg_review_score,
                SUM(CASE WHEN TOTAL_ORDERS > 1 THEN 1 ELSE 0 END) as repeat_customers,
                DIV0(SUM(CASE WHEN TOTAL_ORDERS > 1 THEN 1 ELSE 0 END),
                     COUNT(DISTINCT CUSTOMER_ID)) as repeat_rate
            FROM RETAILLENS_DB.RAW_MART.DIM_CUSTOMERS
            WHERE COHORT_MONTH IS NOT NULL
            GROUP BY DATE_TRUNC('month', COHORT_MONTH)
            ORDER BY cohort_month
        """)

    df.columns = [c.lower() for c in df.columns]
    df["cohort_month"] = pd.to_datetime(df["cohort_month"])
    df["cohort_label"] = df["cohort_month"].dt.strftime("%Y-%m")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Cohorts", len(df))
    col2.metric("Avg Repeat Rate", f"{df['repeat_rate'].mean():.1%}")
    col3.metric("Avg LTV", f"R$ {df['avg_ltv'].mean():,.2f}")

    st.subheader("Cohort Size Over Time")
    fig1 = px.bar(
        df,
        x="cohort_label",
        y="cohort_size",
        color="repeat_rate",
        color_continuous_scale="Blues",
        labels={"cohort_label": "Cohort Month", "cohort_size": "New Customers", "repeat_rate": "Repeat Rate"},
        title="New Customers by Acquisition Month (color = repeat rate)",
    )
    fig1.update_layout(height=400, xaxis_tickangle=45)
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader("Repeat Purchase Rate by Cohort")
    fig2 = px.line(
        df,
        x="cohort_label",
        y="repeat_rate",
        markers=True,
        labels={"cohort_label": "Cohort Month", "repeat_rate": "Repeat Rate"},
        title="Repeat Purchase Rate Trend by Cohort",
    )
    fig2.update_yaxes(tickformat=".1%")
    fig2.update_layout(height=400, xaxis_tickangle=45)
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Lifetime Value by Cohort")
    fig3 = px.bar(
        df,
        x="cohort_label",
        y="avg_ltv",
        color="avg_orders",
        color_continuous_scale="Greens",
        labels={"cohort_label": "Cohort Month", "avg_ltv": "Avg Lifetime Value (R$)", "avg_orders": "Avg Orders"},
        title="Average Lifetime Value by Cohort (color = avg orders)",
    )
    fig3.update_layout(height=400, xaxis_tickangle=45)
    st.plotly_chart(fig3, use_container_width=True)

    with st.expander("Raw cohort data"):
        st.dataframe(df, use_container_width=True)
