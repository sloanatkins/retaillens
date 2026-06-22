import streamlit as st
import plotly.express as px
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from connection import run_query

def render():
    st.title("Seller Scorecard")
    st.markdown("Which sellers are outliers in review score, delivery speed, or order volume?")

    with st.spinner("Loading data..."):
        df = run_query("""
            SELECT
                SELLER_ID,
                STATE,
                CITY,
                TOTAL_ORDERS,
                TOTAL_REVENUE,
                AVG_REVIEW_SCORE,
                AVG_DELIVERY_DELTA_DAYS,
                CANCELLATION_RATE
            FROM RETAILLENS_DB.RAW_MART.DIM_SELLERS
            WHERE TOTAL_ORDERS IS NOT NULL
              AND TOTAL_ORDERS >= 10
            ORDER BY TOTAL_REVENUE DESC
        """)

    df.columns = [c.lower() for c in df.columns]

    st.sidebar.subheader("Filters")
    states = ["All"] + sorted(df["state"].dropna().unique().tolist())
    selected_state = st.sidebar.selectbox("State", states)
    min_orders = st.sidebar.slider("Minimum orders", 10, 500, 50, step=10)

    if selected_state != "All":
        df = df[df["state"] == selected_state]
    df = df[df["total_orders"] >= min_orders]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Sellers", len(df))
    col2.metric("Avg Review Score", f"{df['avg_review_score'].mean():.2f}")
    col3.metric("Avg Delivery Delta", f"{df['avg_delivery_delta_days'].mean():.1f} days")
    col4.metric("Total Revenue", f"R$ {df['total_revenue'].sum():,.0f}")

    st.subheader("Review Score vs Delivery Speed")
    st.caption("Bubble size = order volume. Green = on time or early. Red = late.")
    fig = px.scatter(
        df,
        x="avg_delivery_delta_days",
        y="avg_review_score",
        size="total_orders",
        color="avg_review_score",
        hover_name="seller_id",
        hover_data={"state": True, "total_orders": True, "total_revenue": True},
        color_continuous_scale="RdYlGn",
        labels={
            "avg_delivery_delta_days": "Avg Delivery Delta (days, negative = early)",
            "avg_review_score": "Avg Review Score (1-5)",
            "total_orders": "Total Orders",
        },
        title="Seller Performance Matrix",
    )
    fig.add_vline(x=0, line_dash="dash", line_color="gray", annotation_text="On time")
    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Top 20 Sellers by Revenue")
    fig2 = px.bar(
        df.head(20),
        x="seller_id",
        y="total_revenue",
        color="avg_review_score",
        color_continuous_scale="Blues",
        labels={"total_revenue": "Total Revenue (R$)", "seller_id": "Seller ID"},
        title="Top 20 Sellers by Revenue",
    )
    fig2.update_layout(height=400, xaxis_tickangle=45)
    st.plotly_chart(fig2, use_container_width=True)

    with st.expander("Raw data"):
        st.dataframe(df, use_container_width=True)
