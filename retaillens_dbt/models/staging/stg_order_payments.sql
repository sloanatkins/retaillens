-- stg_order_payments.sql
--
-- Renames and casts the raw order payments table. One order can have multiple
-- rows here if the customer split payment across methods (e.g. credit card +
-- voucher) — the aggregation into total_payment_value happens in
-- int_orders_enriched, not here.

with source as (
    select * from {{ source('retaillens_raw', 'olist_order_payments') }}
),

renamed as (
    select
        order_id,
        try_to_number(payment_sequential)       as payment_sequential,
        payment_type,
        try_to_number(payment_installments)     as payment_installments,
        try_to_decimal(payment_value, 10, 2)    as payment_value
    from source
    where order_id is not null
      and payment_value is not null
)

select * from renamed