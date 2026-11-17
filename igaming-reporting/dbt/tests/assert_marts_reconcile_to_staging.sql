-- FAILS if modelling dropped or duplicated money between staging and the KPI mart
-- (e.g. a bad join). Compares grand totals per metric.
with staged as (
    select
        (select sum(amount) from {{ ref('stg_crm__transactions') }}
          where is_completed and transaction_type = 'deposit')       as deposits,
        (select sum(amount) from {{ ref('stg_crm__transactions') }}
          where is_completed and transaction_type = 'withdrawal')    as withdrawals,
        (select sum(stake) from {{ ref('stg_crm__bets') }} where is_settled)   as turnover,
        (select sum(payout) from {{ ref('stg_crm__bets') }} where is_settled)  as payouts,
        (select sum(amount) from {{ ref('stg_crm__bonus_events') }} where is_bonus_cost) as bonus_cost
),

modelled as (
    select sum(deposits) as deposits, sum(withdrawals) as withdrawals, sum(turnover) as turnover,
           sum(payouts) as payouts, sum(bonus_cost) as bonus_cost
    from {{ ref('fct_daily_kpis') }}
)

select 'deposits' as metric, s.deposits as staged, m.deposits as modelled from staged s, modelled m where abs(s.deposits - m.deposits) > 0.01
union all
select 'withdrawals', s.withdrawals, m.withdrawals from staged s, modelled m where abs(s.withdrawals - m.withdrawals) > 0.01
union all
select 'turnover', s.turnover, m.turnover from staged s, modelled m where abs(s.turnover - m.turnover) > 0.01
union all
select 'payouts', s.payouts, m.payouts from staged s, modelled m where abs(s.payouts - m.payouts) > 0.01
union all
select 'bonus_cost', s.bonus_cost, m.bonus_cost from staged s, modelled m where abs(s.bonus_cost - m.bonus_cost) > 0.01
