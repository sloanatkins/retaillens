-- int_orders_enriched.sql
--
-- Joins orders to their payments and reviews so downstream models
-- don't have to do it themselves.
--
-- Payments are aggregated to one row per order (some orders have multiple
-- payment methods, like card + voucher). Reviews are also aggregated in
-- case an order has more than one review, though that's rare in this dataset.
--
-- delivery_delta_days is positive when the order arrived late and negative
-- when it arrived early. NULL means it hasn't been delivered yet.

with orders as (
    select * from {{ ref('stg_orders') }}
),

payments as (
    select
        order_id,
        sum(payment_value)        as total_payment_value,
        max(payment_installments) as max_installments,
        count(*)                  as payment_count
    from {{ ref('stg_order_payments') }}
    group by order_id
),

reviews as (
    select
        order_id,
        avg(review_score) as avg_review_score,
        count(*)          as review_count
    from {{ ref('stg_order_reviews') }}
    group by order_id
),

enriched as (
    select
        o.order_id,
        o.customer_id,
        o.order_status,
        o.order_purchase_ts,
        o.order_approved_ts,
        o.order_delivered_customer_ts,
        o.order_estimated_delivery_ts,
        -- positive = late, negative = early, null = not delivered yet
        datediff(
            day,
            o.order_estimated_delivery_ts,
            o.order_delivered_customer_ts
        )                         as delivery_delta_days,
        p.total_payment_value,
        p.max_installments,
        p.payment_count,
        r.avg_review_score,
        r.review_count
    from orders o
    left join payments p on o.order_id = p.order_id
    left join reviews r  on o.order_id = r.order_id
)

select * from enriched