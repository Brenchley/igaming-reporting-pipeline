with ranked as (
    select
        *,
        row_number() over (partition by bonus_event_id order by _loaded_at desc) as _rn
    from {{ source('crm', 'bonus_events') }}
)

select
    bonus_event_id,
    bonus_id,
    player_id,
    bonus_type,
    event_type,
    {{ money('amount') }}                  as amount,
    event_type in (
        {%- for t in var('bonus_cost_event_types') %}'{{ t }}'{% if not loop.last %}, {% endif %}{% endfor -%}
    )                                      as is_bonus_cost,
    event_at,
    {{ to_local_date('event_at') }}        as event_date
from ranked
where _rn = 1
