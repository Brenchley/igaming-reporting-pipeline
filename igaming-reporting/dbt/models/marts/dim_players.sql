with players as (
    select * from {{ ref('stg_crm__players') }}
),

ftd as (
    select player_id, first_deposit_at, first_deposit_date, first_deposit_amount
    from (
        select
            player_id,
            created_at       as first_deposit_at,
            transaction_date as first_deposit_date,
            amount           as first_deposit_amount,
            row_number() over (partition by player_id order by created_at, transaction_id) as rn
        from {{ ref('stg_crm__transactions') }}
        where is_completed and transaction_type = 'deposit'
    ) d
    where rn = 1
),

lifetime as (
    select
        player_id,
        max(activity_date)   as last_active_date,
        sum(deposits)        as lifetime_deposits,
        sum(turnover - payouts) as lifetime_ggr,
        sum(bonus_cost)      as lifetime_bonus_cost
    from {{ ref('int_player_daily_activity') }}
    group by 1
)

select
    p.player_id,
    p.email_hash,
    p.mobile_hash,
    p.birth_year,
    case
        when p.birth_year is null then 'unknown'
        when extract(year from current_date) - p.birth_year < 25 then '18-24'
        when extract(year from current_date) - p.birth_year < 35 then '25-34'
        when extract(year from current_date) - p.birth_year < 45 then '35-44'
        when extract(year from current_date) - p.birth_year < 55 then '45-54'
        else '55+'
    end                                                as age_band,
    p.province,
    p.registration_channel,
    p.registered_at,
    p.registration_date,
    p.kyc_status,
    p.marketing_opt_in,
    p.account_status,
    ftd.first_deposit_at,
    ftd.first_deposit_date,
    ftd.first_deposit_amount,
    ftd.player_id is not null                         as has_deposited,
    l.last_active_date,
    coalesce(l.lifetime_deposits, 0)                  as lifetime_deposits,
    coalesce(l.lifetime_ggr, 0)                       as lifetime_ggr,
    coalesce(l.lifetime_bonus_cost, 0)                as lifetime_bonus_cost,
    case
        when coalesce(l.lifetime_deposits, 0) >= 50000 then 'VIP'
        when coalesce(l.lifetime_deposits, 0) >= 5000  then 'High'
        when coalesce(l.lifetime_deposits, 0) > 0      then 'Standard'
        else 'Non-depositor'
    end                                                as value_segment
from players p
left join ftd      on ftd.player_id = p.player_id
left join lifetime l on l.player_id = p.player_id
