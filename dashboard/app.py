import streamlit as st

st.set_page_config(
    page_title="RetailLens",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

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

if page == "Category Performance":
    from views.category_performance import render
    render()
elif page == "Seller Scorecard":
    from views.seller_scorecard import render
    render()
elif page == "Customer Cohorts":
    from views.customer_cohorts import render
    render()
