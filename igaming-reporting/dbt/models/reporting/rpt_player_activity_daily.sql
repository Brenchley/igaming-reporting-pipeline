{{ config(
    partition_by=({'field': 'activity_date', 'data_type': 'date'} if target.type == 'bigquery' else none),
    cluster_by=(['province', 'value_segment'] if target.type == 'bigquery' else none)
) }}
-- Looker Studio self-serve source: one wide, pre-joined row per player per day.
-- Business users can slice any measure by any player attribute without writing SQL or joins.
-- Contains pseudonymous player_id only (no direct identifiers).
select
    f.activity_date,
    {{ dbt.date_trunc('month', 'f.activity_date') }}       as activity_month,
    f.player_id,
    p.province,
    p.registration_channel,
    p.age_band,
    p.kyc_status,
    p.value_segment,
    p.account_status,
    p.marketing_opt_in,
    {{ dbt.date_trunc('month', 'p.registration_date') }}   as registration_cohort,
    {{ dbt.date_trunc('month', 'p.first_deposit_date') }}  as ftd_cohort,
    f.is_ftd_day,
    f.is_active,
    f.is_depositor,
    f.deposits,
    f.deposit_count,
    f.withdrawals,
    f.net_deposits,
    f.turnover,
    f.casino_stakes,
    f.sportsbook_stakes,
    f.payouts,
    f.bets_settled,
    f.ggr,
    f.casino_ggr,
    f.sportsbook_ggr,
    f.bonus_granted,
    f.bonus_cost,
    f.ngr
from {{ ref('fct_player_daily') }} f
left join {{ ref('dim_players') }} p on p.player_id = f.player_id
