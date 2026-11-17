{{ config(
    partition_by=({'field': 'activity_date', 'data_type': 'date'} if target.type == 'bigquery' else none),
    cluster_by=(['player_id'] if target.type == 'bigquery' else none)
) }}

select
    a.player_id,
    a.activity_date,
    a.deposits,
    a.deposit_count,
    a.withdrawals,
    a.deposits - a.withdrawals                              as net_deposits,
    a.cash_stakes,
    a.bonus_stakes,
    a.turnover,
    a.payouts,
    a.bets_settled,
    a.turnover - a.payouts                                  as ggr,
    a.casino_stakes - a.casino_payouts                      as casino_ggr,
    a.sportsbook_stakes - a.sportsbook_payouts              as sportsbook_ggr,
    a.casino_stakes,
    a.sportsbook_stakes,
    a.bonus_granted,
    a.bonus_cost,
    {{ ngr('(a.turnover - a.payouts)', 'a.bonus_cost') }}   as ngr,
    a.bets_settled > 0                                      as is_active,
    a.deposit_count > 0                                     as is_depositor,
    a.activity_date = p.first_deposit_date                  as is_ftd_day
from {{ ref('int_player_daily_activity') }} a
left join {{ ref('dim_players') }} p on p.player_id = a.player_id
