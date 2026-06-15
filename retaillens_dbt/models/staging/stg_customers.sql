with source as (
    select * from {{ source('retaillens_raw', 'olist_customers') }}
),

renamed as (
    select
        customer_id,
        customer_unique_id,
        customer_zip_code_prefix as zip_prefix,
        customer_city            as city,
        customer_state           as state
    from source
    where customer_id is not null
      and customer_unique_id is not null
)

select * from renamed
