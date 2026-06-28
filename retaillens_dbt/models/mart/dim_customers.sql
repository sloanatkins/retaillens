-- dim_customers.sql
--
-- Customer dimension with lifetime value metrics and geolocation coordinates.
-- Pulls from int_customer_lifetime_value (which already has the order rollup)
-- and joins stg_geolocation to add lat/lng for the customer's zip code.
--
-- The surrogate key (customer_sk) is md5 of customer_id. customer_unique_id
-- is the Olist de-duplicated ID — one customer can have multiple customer_ids
-- across orders but only one unique_id.

with clv as (
    select * from {{ ref('int_customer_lifetime_value') }}
),

geolocation as (
    select * from {{ ref('stg_geolocation') }}
),

final as (
    select
        md5(c.customer_id)  as customer_sk,
        c.customer_id,
        c.customer_unique_id,
        c.city,
        c.state,
        c.zip_prefix,
        g.lat               as geo_lat,
        g.lng               as geo_lng,
        c.first_order_ts,
        c.last_order_ts,
        c.total_orders,
        c.lifetime_value,
        c.avg_order_value,
        c.avg_review_score,
        c.cohort_month,
        c.customer_tenure_days
    from clv c
    left join geolocation g on c.zip_prefix = g.zip_prefix
)

select * from final