with ranked as (
    select
        *,
        row_number() over (partition by player_id order by updated_at desc, _loaded_at desc) as _rn
    from {{ source('crm', 'players') }}
)

select
    player_id,
    email_hash,
    mobile_hash,
    birth_year,
    province,
    registration_channel,
    registered_at,
    {{ to_local_date('registered_at') }}      as registration_date,
    kyc_status,
    marketing_opt_in,
    status                                    as account_status,
    updated_at
from ranked
where _rn = 1
