with products as (
    select * from {{ ref('stg_products') }}
),

final as (
    select
        md5(product_id)         as product_sk,
        product_id,
        category_name_english,
        weight_g,
        length_cm,
        height_cm,
        width_cm,
        volume_cm3
    from products
)

select * from final
