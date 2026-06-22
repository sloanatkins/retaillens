import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from connection import run_query

def render():
    st.title("Category Performance")
    st.markdown("Which product categories drive the most revenue — and which have the highest cancellation rates?")

    with st.spinner("Loading data..."):
        df = run_query("""
            SELECT
                p.CATEGORY_NAME_ENGLISH as category,
                COUNT(DISTINCT f.ORDER_ID) as total_orders,
                SUM(f.PRICE) as total_revenue,
                AVG(f.REVIEW_SCORE) as avg_review_score,
                SUM(CASE WHEN f.ORDER_STATUS = 'canceled' THEN 1 ELSE 0 END) as canceled_orders,
                DIV0(SUM(CASE WHEN f.ORDER_STATUS = 'canceled' THEN 1 ELSE 0 END),
                     COUNT(DISTINCT f.ORDER_ID)) as cancellation_rate
            FROM RETAILLENS_DB.RAW_MART.FCT_ORDER_ITEMS f
            LEFT JOIN RETAILLENS_DB.RAW_MART.DIM_PRODUCTS p ON f.PRODUCT_SK = p.PRODUCT_SK
            WHERE p.CATEGORY_NAME_ENGLISH != 'unknown'
            GROUP BY p.CATEGORY_NAME_ENGLISH
            ORDER BY total_revenue DESC
            LIMIT 20
        """)

    df.columns = [c.lower() for c in df.columns]

    st.sidebar.subheader("Filters")
    min_orders = st.sidebar.slider("Minimum orders", 100, 5000, 500, step=100)
    df = df[df["total_orders"] >= min_orders]

    col1, col2, col3 = st.columns(3)
    col1.metric("Categories shown", len(df))
    col2.metric("Total Revenue", f"R$ {df['total_revenue'].sum():,.0f}")
    col3.metric("Avg Review Score", f"{df['avg_review_score'].mean():.2f}")

    st.subheader("Revenue by Category")
    fig1 = px.bar(
        df.head(15),
        x="total_revenue",
        y="category",
        orientation="h",
        color="avg_review_score",
        color_continuous_scale="Blues",
        labels={"total_revenue": "Total Revenue (R$)", "category": "Category", "avg_review_score": "Avg Review"},
        title="Top 15 Categories by Revenue",
    )
    fig1.update_layout(height=500, yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader("Revenue vs Cancellation Rate")
    fig2 = px.scatter(
        df,
        x="total_revenue",
        y="cancellation_rate",
        size="total_orders",
        color="avg_review_score",
        hover_name="category",
        color_continuous_scale="RdYlGn",
        labels={
            "total_revenue": "Total Revenue (R$)",
            "cancellation_rate": "Cancellation Rate",
            "total_orders": "Total Orders",
            "avg_review_score": "Avg Review Score",
        },
        title="Revenue vs Cancellation Rate (bubble size = order volume)",
    )
    fig2.update_layout(height=450)
    st.plotly_chart(fig2, use_container_width=True)

    with st.expander("Raw data"):
        st.dataframe(df, use_container_width=True)
