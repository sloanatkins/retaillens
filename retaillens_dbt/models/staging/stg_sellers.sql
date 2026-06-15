with source as (
    select * from {{ source('retaillens_raw', 'olist_sellers') }}
),

renamed as (
    select
        seller_id,
        seller_zip_code_prefix as zip_prefix,
        seller_city            as city,
        seller_state           as state
    from source
    where seller_id is not null
)

select * from renamed
