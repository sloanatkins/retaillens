-- dim_dates.sql
--
-- Date dimension covering 2016-01-01 through 2019-12-31 (1,461 days = 4 years).
-- Generated entirely in Snowflake using seq4() — no source table needed.
-- The date_sk is a YYYYMMDD integer string so it's easy to join against
-- timestamp columns after casting (e.g. to_char(order_ts, 'YYYYMMDD')).

with date_spine as (
    -- seq4() generates sequential integers starting at 0; adding them to the
    -- anchor date gives us one row per day for the full range of the dataset
    select
        dateadd(day, seq4(), '2016-01-01'::date) as full_date
    from table(generator(rowcount => 1461))
),

final as (
    select
        to_char(full_date, 'YYYYMMDD')  as date_sk,
        full_date,
        year(full_date)                 as year,
        month(full_date)                as month,
        quarter(full_date)              as quarter,
        dayofweek(full_date)            as day_of_week,  -- 0 = Sunday, 6 = Saturday in Snowflake
        case
            when dayofweek(full_date) in (0, 6) then true
            else false
        end                             as is_weekend,
        monthname(full_date)            as month_name
    from date_spine
)

select * from final