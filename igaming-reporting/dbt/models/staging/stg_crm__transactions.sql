with ranked as (
    select
        *,
        row_number() over (partition by transaction_id order by updated_at desc, _loaded_at desc) as _rn
    from {{ source('crm', 'transactions') }}
)

select
    transaction_id,
    player_id,
    type                                   as transaction_type,
    {{ money('amount') }}                  as amount,
    currency,
    method                                 as payment_method,
    status,
    status = 'completed'                   as is_completed,
    created_at,
    {{ to_local_date('created_at') }}      as transaction_date,
    updated_at
from ranked
where _rn = 1
