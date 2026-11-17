with ranked as (
    select
        *,
        row_number() over (partition by bet_id order by updated_at desc, _loaded_at desc) as _rn
    from {{ source('crm', 'bets') }}
)

select
    bet_id,
    player_id,
    product,
    game_or_sport,
    {{ money('stake') }}                                                      as stake,
    {{ money('payout') }}                                                     as payout,
    is_bonus_bet,
    case when is_bonus_bet then {{ money('stake') }} else {{ money(0) }} end  as bonus_stake,
    case when is_bonus_bet then {{ money(0) }} else {{ money('stake') }} end  as cash_stake,
    status,
    status = 'settled'                                                        as is_settled,
    placed_at,
    {{ to_local_date('placed_at') }}                                          as placed_date,
    settled_at,
    {{ to_local_date('settled_at') }}                                         as settled_date,
    updated_at
from ranked
where _rn = 1
