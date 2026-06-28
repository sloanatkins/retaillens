"""
RetailLens Dashboard
====================

Streamlit app with three views into the Olist Brazilian E-Commerce dataset.

Views:
- Category Performance: revenue and cancellation rates by product category
- Seller Scorecard: review score vs delivery speed, outlier detection
- Customer Cohorts: repeat purchase rate and LTV by acquisition month

Each view lives in its own file under views/ and gets imported on demand
so only the selected page's query runs on each interaction.

Run with:
    streamlit run dashboard/app.py

Dependencies:
- streamlit
- plotly
- snowflake-connector-python
"""

import streamlit as st

# ── Page config ───────────────────────────────────────────────────────
# Has to be the first Streamlit call or it throws
st.set_page_config(
    page_title="RetailLens",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar nav ───────────────────────────────────────────────────────
st.sidebar.title("RetailLens")
st.sidebar.markdown("Brazilian E-Commerce Analytics")
st.sidebar.divider()

page = st.sidebar.radio(
    "Navigate",
    ["Category Performance", "Seller Scorecard", "Customer Cohorts"],
)

st.sidebar.divider()
st.sidebar.caption("Data: Olist Brazilian E-Commerce")
st.sidebar.caption("Warehouse: Snowflake · Transforms: dbt")

# ── Route to the selected view ────────────────────────────────────────
if page == "Category Performance":
    from views.category_performance import render
    render()
elif page == "Seller Scorecard":
    from views.seller_scorecard import render
    render()
elif page == "Customer Cohorts":
    from views.customer_cohorts import render
    render()