with source as (
    select * from {{ source('retaillens_raw', 'olist_order_items') }}
),

renamed as (
    select
        order_id,
        try_to_number(order_item_id)    as order_item_id,
        product_id,
        seller_id,
        try_to_timestamp_ntz(shipping_limit_date) as shipping_limit_ts,
        try_to_decimal(price, 10, 2)         as price,
        try_to_decimal(freight_value, 10, 2) as freight_value
    from source
    where order_id is not null
      and product_id is not null
      and seller_id is not null
)

select * from renamed
