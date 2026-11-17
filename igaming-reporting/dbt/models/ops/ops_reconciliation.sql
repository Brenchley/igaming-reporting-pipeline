-- Our figures vs the platform's own back-office report, per day and metric.
-- Feeds the "Data health" dashboard page, the dbt reconciliation test and the alerting job.
with ours as (
    select report_date, deposits, withdrawals, turnover as stakes, payouts, bonus_cost, ggr
    from {{ ref('fct_daily_kpis') }}
),

platform as (
    select * from {{ ref('stg_crm__daily_summary') }}
),

{% set metrics = ['deposits', 'withdrawals', 'stakes', 'payouts', 'bonus_cost', 'ggr'] %}
long as (
    {% for m in metrics %}
    select
        p.report_date,
        '{{ m }}'                         as metric,
        coalesce(o.{{ m }}, 0)            as our_value,
        p.{{ m }}                         as platform_value,
        p.pulled_at
    from platform p
    left join ours o on o.report_date = p.report_date
    {% if not loop.last %}union all{% endif %}
    {% endfor %}
)

select
    report_date,
    metric,
    our_value,
    platform_value,
    our_value - platform_value                                  as difference,
    case
        when report_date > {{ local_days_ago(var('reconciliation_exclude_recent_days')) }}
            then 'not_checked_partial_day'
        when abs(our_value - platform_value) <= {{ var('reconciliation_tolerance_zar') }}
            then 'match'
        else 'mismatch'
    end                                                         as status,
    pulled_at                                                   as platform_report_pulled_at
from long
