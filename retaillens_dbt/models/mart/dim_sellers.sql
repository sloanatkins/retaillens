-- dim_sellers.sql
--
-- Seller dimension built from int_seller_metrics, which rolls up orders,
-- revenue, review scores, and delivery performance per seller.
-- Only includes sellers with ≥ 10 orders (that filter lives in the intermediate
-- model) so the scorecard isn't skewed by sellers with one or two orders.

with seller_metrics as (
    select * from {{ ref('int_seller_metrics') }}
),

final as (
    select
        md5(seller_id)          as seller_sk,
        seller_id,
        city,
        state,
        zip_prefix,
        total_orders,
        total_items_sold,
        total_revenue,
        avg_item_price,
        avg_review_score,
        avg_delivery_delta_days,    -- positive = late, negative = early
        canceled_orders,
        cancellation_rate,
        first_order_ts,
        last_order_ts
    from seller_metrics
)

select * from final