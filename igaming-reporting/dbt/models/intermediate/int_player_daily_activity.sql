-- One row per player per reporting day with any financial or betting activity.
-- Built by unioning each activity stream then aggregating, so no join fan-out is possible.
with payments as (
    select
        player_id,
        transaction_date as activity_date,
        case when transaction_type = 'deposit' then amount else 0 end      as deposits,
        case when transaction_type = 'deposit' then 1 else 0 end           as deposit_count,
        case when transaction_type = 'withdrawal' then amount else 0 end   as withdrawals,
        0 as cash_stakes, 0 as bonus_stakes, 0 as payouts, 0 as bets_settled,
        0 as casino_stakes, 0 as casino_payouts, 0 as sportsbook_stakes, 0 as sportsbook_payouts,
        0 as bonus_granted, 0 as bonus_cost
    from {{ ref('stg_crm__transactions') }}
    where is_completed
),

betting as (
    select
        player_id,
        settled_date as activity_date,
        0, 0, 0,
        cash_stake, bonus_stake, payout, 1,
        case when product = 'casino' then stake else 0 end,
        case when product = 'casino' then payout else 0 end,
        case when product = 'sportsbook' then stake else 0 end,
        case when product = 'sportsbook' then payout else 0 end,
        0, 0
    from {{ ref('stg_crm__bets') }}
    where is_settled
),

bonuses as (
    select
        player_id,
        event_date as activity_date,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        case when event_type = 'granted' then amount else 0 end,
        case when is_bonus_cost then amount else 0 end
    from {{ ref('stg_crm__bonus_events') }}
),

unioned as (
    select * from payments
    union all select * from betting
    union all select * from bonuses
)

select
    player_id,
    activity_date,
    {{ money('sum(deposits)') }}            as deposits,
    sum(deposit_count)                      as deposit_count,
    {{ money('sum(withdrawals)') }}         as withdrawals,
    {{ money('sum(cash_stakes)') }}         as cash_stakes,
    {{ money('sum(bonus_stakes)') }}        as bonus_stakes,
    {{ money('sum(cash_stakes) + sum(bonus_stakes)') }} as turnover,
    {{ money('sum(payouts)') }}             as payouts,
    sum(bets_settled)                       as bets_settled,
    {{ money('sum(casino_stakes)') }}       as casino_stakes,
    {{ money('sum(casino_payouts)') }}      as casino_payouts,
    {{ money('sum(sportsbook_stakes)') }}   as sportsbook_stakes,
    {{ money('sum(sportsbook_payouts)') }}  as sportsbook_payouts,
    {{ money('sum(bonus_granted)') }}       as bonus_granted,
    {{ money('sum(bonus_cost)') }}          as bonus_cost
from unioned
group by 1, 2
