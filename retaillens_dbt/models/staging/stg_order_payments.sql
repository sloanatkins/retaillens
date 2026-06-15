with source as (
    select * from {{ source('retaillens_raw', 'olist_order_payments') }}
),

renamed as (
    select
        order_id,
        try_to_number(payment_sequential)    as payment_sequential,
        payment_type,
        try_to_number(payment_installments)  as payment_installments,
        try_to_decimal(payment_value, 10, 2) as payment_value
    from source
    where order_id is not null
      and payment_value is not null
)

select * from renamed
