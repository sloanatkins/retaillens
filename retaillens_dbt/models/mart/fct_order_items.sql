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
        o.delivery_delta_days,
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
