with seller_metrics as (
    select * from {{ ref('int_seller_metrics') }}
),

final as (
    select
        md5(seller_id)              as seller_sk,
        seller_id,
        city,
        state,
        zip_prefix,
        total_orders,
        total_items_sold,
        total_revenue,
        avg_item_price,
        avg_review_score,
        avg_delivery_delta_days,
        canceled_orders,
        cancellation_rate,
        first_order_ts,
        last_order_ts
    from seller_metrics
)

select * from final
