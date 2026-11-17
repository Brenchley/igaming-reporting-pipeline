-- Latest version of the platform's report for each day (the platform restates recent days).
with ranked as (
    select
        *,
        row_number() over (partition by report_date order by _loaded_at desc) as _rn
    from {{ source('crm', 'crm_daily_summary') }}
)

select
    report_date,
    {{ money('deposits') }}        as deposits,
    {{ money('withdrawals') }}     as withdrawals,
    {{ money('stakes') }}          as stakes,
    {{ money('payouts') }}         as payouts,
    {{ money('bonus_released') }}  as bonus_cost,
    {{ money('ggr') }}             as ggr,
    _loaded_at                     as pulled_at
from ranked
where _rn = 1
