with source as (
    select * from {{ source('retaillens_raw', 'olist_orders') }}
),

renamed as (
    select
        order_id,
        customer_id,
        order_status,
        try_to_timestamp_ntz(order_purchase_timestamp) as order_purchase_ts,
        try_to_timestamp_ntz(order_approved_at)         as order_approved_ts,
        try_to_timestamp_ntz(order_delivered_carrier_date) as order_delivered_carrier_ts,
        try_to_timestamp_ntz(order_delivered_customer_date) as order_delivered_customer_ts,
        try_to_timestamp_ntz(order_estimated_delivery_date) as order_estimated_delivery_ts
    from source
    where order_id is not null
      and customer_id is not null
)

select * from renamed
