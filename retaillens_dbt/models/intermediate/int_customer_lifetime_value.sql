with orders as (
    select * from {{ ref('int_orders_enriched') }}
),

customers as (
    select * from {{ ref('stg_customers') }}
),

order_agg as (
    select
        customer_id,
        min(order_purchase_ts)          as first_order_ts,
        max(order_purchase_ts)          as last_order_ts,
        count(*)                        as total_orders,
        sum(total_payment_value)        as lifetime_value,
        avg(total_payment_value)        as avg_order_value,
        avg(avg_review_score)           as avg_review_score,
        date_trunc('month', min(order_purchase_ts)) as cohort_month
    from orders
    where order_status not in ('canceled', 'unavailable')
    group by customer_id
),

final as (
    select
        c.customer_id,
        c.customer_unique_id,
        c.city,
        c.state,
        c.zip_prefix,
        o.first_order_ts,
        o.last_order_ts,
        o.total_orders,
        o.lifetime_value,
        o.avg_order_value,
        o.avg_review_score,
        o.cohort_month,
        datediff(
            day,
            o.first_order_ts,
            o.last_order_ts
        ) as customer_tenure_days
    from customers c
    left join order_agg o on c.customer_id = o.customer_id
)

select * from final
