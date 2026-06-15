with source as (
    select * from {{ source('retaillens_raw', 'olist_products') }}
),

translation as (
    select * from {{ source('retaillens_raw', 'product_category_translation') }}
),

renamed as (
    select
        s.product_id,
        coalesce(t.product_category_name_english, 'unknown') as category_name_english,
        try_to_number(s.product_weight_g)    as weight_g,
        try_to_number(s.product_length_cm)   as length_cm,
        try_to_number(s.product_height_cm)   as height_cm,
        try_to_number(s.product_width_cm)    as width_cm,
        try_to_number(s.product_length_cm) *
        try_to_number(s.product_height_cm) *
        try_to_number(s.product_width_cm)    as volume_cm3
    from source s
    left join translation t
        on s.product_category_name = t.product_category_name
    where s.product_id is not null
)

select * from renamed
