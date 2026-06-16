with order_items as (
    select * from {{ ref('stg_order_items') }}
),

orders as (
    select * from {{ ref('int_orders_enriched') }}
),

sellers as (
    select * from {{ ref('stg_sellers') }}
),

seller_agg as (
    select
        oi.seller_id,
        count(distinct oi.order_id)         as total_orders,
        count(*)                            as total_items_sold,
        sum(oi.price)                       as total_revenue,
        avg(oi.price)                       as avg_item_price,
        avg(o.avg_review_score)             as avg_review_score,
        avg(o.delivery_delta_days)          as avg_delivery_delta_days,
        sum(case when o.order_status = 'canceled'
            then 1 else 0 end)              as canceled_orders,
        min(o.order_purchase_ts)            as first_order_ts,
        max(o.order_purchase_ts)            as last_order_ts
    from order_items oi
    left join orders o on oi.order_id = o.order_id
    group by oi.seller_id
),

final as (
    select
        s.seller_id,
        s.city,
        s.state,
        s.zip_prefix,
        a.total_orders,
        a.total_items_sold,
        a.total_revenue,
        a.avg_item_price,
        a.avg_review_score,
        a.avg_delivery_delta_days,
        a.canceled_orders,
        a.first_order_ts,
        a.last_order_ts,
        div0(a.canceled_orders, a.total_orders) as cancellation_rate
    from sellers s
    left join seller_agg a on s.seller_id = a.seller_id
)

select * from final
