-- Looker Studio source: company KPIs by day. Additive measures only; ratios
-- (hold %, ARPU, avg deposit) are Looker Studio calculated fields so they aggregate correctly.
select
    report_date,
    {{ dbt.date_trunc('week', 'report_date') }}   as report_week,
    {{ dbt.date_trunc('month', 'report_date') }}  as report_month,
    registrations,
    ftd_count,
    ftd_amount,
    depositors,
    active_players,
    deposits,
    deposit_count,
    withdrawals,
    net_deposits,
    turnover,
    cash_stakes,
    bonus_stakes,
    payouts,
    bets_settled,
    ggr,
    casino_ggr,
    sportsbook_ggr,
    bonus_granted,
    bonus_cost,
    ngr
from {{ ref('fct_daily_kpis') }}
