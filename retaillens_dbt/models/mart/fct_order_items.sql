-- fct_order_items.sql
--
-- Fact table at the order-item grain — one row per item per order.
-- Joins to all four dimensions so the dashboard can slice by customer,
-- product, seller, or date without needing to touch the raw tables.
--
-- The surrogate key is md5 of order_id + order_item_id because an order
-- can have multiple items and order_item_id alone isn't globally unique.
-- dim_sellers only includes sellers with ≥ 10 orders, so s.seller_sk will
-- be null for low-volume sellers — that's expected.

with order_items as (
    select * from {{ ref('stg_order_items') }}
),

orders as (
    select * from {{ ref('int_orders_enriched') }}
),

customers as (
    select * from {{ ref('dim_customers') }}
),

products as (
    select * from {{ ref('dim_products') }}
),

sellers as (
    select * from {{ ref('dim_sellers') }}
),

dates as (
    select * from {{ ref('dim_dates') }}
),

final as (
    select
        md5(oi.order_id || '-' || oi.order_item_id::varchar) as order_item_sk,
        oi.order_id,
        oi.order_item_id,
        c.customer_sk,
        p.product_sk,
        s.seller_sk,
        d.date_sk,
        oi.price,
        oi.freight_value,
        o.avg_review_score       as review_score,
        o.order_status,
        o.delivery_delta_days,   -- positive = late, negative = early, null = not delivered
        o.total_payment_value,
        o.order_purchase_ts
    from order_items oi
    left join orders o
        on oi.order_id = o.order_id
    left join customers c
        on o.customer_id = c.customer_id
    left join products p
        on oi.product_id = p.product_id
    left join sellers s
        on oi.seller_id = s.seller_id
    left join dates d
        on to_char(o.order_purchase_ts, 'YYYYMMDD') = d.date_sk
)

select * from final