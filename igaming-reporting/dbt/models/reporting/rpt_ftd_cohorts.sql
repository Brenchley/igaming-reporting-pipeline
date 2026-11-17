-- Retention and value by first-deposit month cohort.
with base as (
    select
        {{ dbt.date_trunc('month', 'p.first_deposit_date') }}  as ftd_cohort,
        {{ dbt.date_trunc('month', 'f.activity_date') }}       as activity_month,
        f.player_id,
        f.deposits,
        f.ngr,
        f.is_active
    from {{ ref('fct_player_daily') }} f
    join {{ ref('dim_players') }} p on p.player_id = f.player_id
    where p.has_deposited
      and f.activity_date >= p.first_deposit_date
),

cohort_size as (
    select {{ dbt.date_trunc('month', 'first_deposit_date') }} as ftd_cohort, count(*) as cohort_players
    from {{ ref('dim_players') }}
    where has_deposited
    group by 1
)

select
    b.ftd_cohort,
    b.activity_month,
    {{ dbt.datediff('b.ftd_cohort', 'b.activity_month', 'month') }}  as months_since_ftd,
    s.cohort_players,
    count(distinct case when b.is_active then b.player_id end)      as active_players,
    sum(b.deposits)                                                  as deposits,
    sum(b.ngr)                                                       as ngr
from base b
join cohort_size s on s.ftd_cohort = b.ftd_cohort
group by 1, 2, 3, 4
