with date_spine as (
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
        dayofweek(full_date)            as day_of_week,
        case when dayofweek(full_date) in (0, 6)
            then true else false end    as is_weekend,
        monthname(full_date)            as month_name
    from date_spine
)

select * from final
