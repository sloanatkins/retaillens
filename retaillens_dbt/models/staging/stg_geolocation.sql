with source as (
    select * from {{ source('retaillens_raw', 'olist_geolocation') }}
),

deduplicated as (
    select
        geolocation_zip_code_prefix as zip_prefix,
        try_to_decimal(geolocation_lat, 18, 6) as lat,
        try_to_decimal(geolocation_lng, 18, 6) as lng,
        geolocation_city as city,
        geolocation_state as state,
        row_number() over (
            partition by geolocation_zip_code_prefix
            order by geolocation_zip_code_prefix
        ) as row_num
    from source
    where geolocation_zip_code_prefix is not null
)

select
    zip_prefix,
    lat,
    lng,
    city,
    state
from deduplicated
where row_num = 1
