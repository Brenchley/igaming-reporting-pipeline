{{ config(
    partition_by=({'field': 'report_date', 'data_type': 'date'} if target.type == 'bigquery' else none)
) }}

with activity as (
    select
        activity_date                                   as report_date,
        sum(deposits)                                   as deposits,
        sum(deposit_count)                              as deposit_count,
        sum(withdrawals)                                as withdrawals,
        sum(turnover)                                   as turnover,
        sum(cash_stakes)                                as cash_stakes,
        sum(bonus_stakes)                               as bonus_stakes,
        sum(payouts)                                    as payouts,
        sum(ggr)                                        as ggr,
        sum(casino_ggr)                                 as casino_ggr,
        sum(sportsbook_ggr)                             as sportsbook_ggr,
        sum(bonus_granted)                              as bonus_granted,
        sum(bonus_cost)                                 as bonus_cost,
        sum(ngr)                                        as ngr,
        sum(bets_settled)                               as bets_settled,
        count(distinct case when is_active then player_id end)     as active_players,
        count(distinct case when is_depositor then player_id end)  as depositors,
        count(distinct case when is_ftd_day then player_id end)    as ftd_count
    from {{ ref('fct_player_daily') }}
    group by 1
),

registrations as (
    select registration_date as report_date, count(*) as registrations
    from {{ ref('dim_players') }}
    group by 1
),

ftd_amounts as (
    select first_deposit_date as report_date, sum(first_deposit_amount) as ftd_amount
    from {{ ref('dim_players') }}
    where has_deposited
    group by 1
),

calendar as (
    select report_date from activity
    union distinct
    select report_date from registrations
)

select
    c.report_date,
    coalesce(r.registrations, 0)                 as registrations,
    coalesce(a.ftd_count, 0)                     as ftd_count,
    coalesce(f.ftd_amount, 0)                    as ftd_amount,
    coalesce(a.depositors, 0)                    as depositors,
    coalesce(a.active_players, 0)                as active_players,
    coalesce(a.deposits, 0)                      as deposits,
    coalesce(a.deposit_count, 0)                 as deposit_count,
    coalesce(a.withdrawals, 0)                   as withdrawals,
    coalesce(a.deposits, 0) - coalesce(a.withdrawals, 0) as net_deposits,
    coalesce(a.turnover, 0)                      as turnover,
    coalesce(a.cash_stakes, 0)                   as cash_stakes,
    coalesce(a.bonus_stakes, 0)                  as bonus_stakes,
    coalesce(a.payouts, 0)                       as payouts,
    coalesce(a.bets_settled, 0)                  as bets_settled,
    coalesce(a.ggr, 0)                           as ggr,
    coalesce(a.casino_ggr, 0)                    as casino_ggr,
    coalesce(a.sportsbook_ggr, 0)                as sportsbook_ggr,
    coalesce(a.bonus_granted, 0)                 as bonus_granted,
    coalesce(a.bonus_cost, 0)                    as bonus_cost,
    coalesce(a.ngr, 0)                           as ngr,
    {{ safe_divide('a.ggr', 'a.turnover') }}     as hold_pct
from calendar c
left join activity      a on a.report_date = c.report_date
left join registrations r on r.report_date = c.report_date
left join ftd_amounts   f on f.report_date = c.report_date
