-- dim_products.sql
--
-- Product dimension pulled straight from stg_products, which already handles
-- the category name translation join and the volume calculation.
-- The surrogate key is md5 of product_id.

with products as (
    select * from {{ ref('stg_products') }}
),

final as (
    select
        md5(product_id)     as product_sk,
        product_id,
        category_name_english,
        weight_g,
        length_cm,
        height_cm,
        width_cm,
        volume_cm3          -- length * height * width, computed in staging
    from products
)

select * from final