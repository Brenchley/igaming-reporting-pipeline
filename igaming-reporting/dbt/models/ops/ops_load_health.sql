-- Latest ingestion state per resource. Drives freshness alerts and the "Data health" page.
with audit as (
    select * from {{ source('ops', 'load_audit') }}
),

last_success as (
    select resource, max(finished_at) as last_success_at
    from audit where status = 'success'
    group by 1
),

latest as (
    select
        resource, status as last_status, finished_at as last_run_at, error as last_error,
        row_number() over (partition by resource order by started_at desc) as rn
    from audit
),

recent_failures as (
    select resource, count(*) as failures_24h
    from audit
    where status = 'failed'
      and started_at >= {{ ts_hours_ago(24) }}
    group by 1
)

select
    l.resource,
    l.last_status,
    l.last_run_at,
    l.last_error,
    s.last_success_at,
    {{ hours_between('s.last_success_at', current_ts()) }}   as hours_since_success,
    coalesce(f.failures_24h, 0)                               as failures_24h,
    coalesce({{ hours_between('s.last_success_at', current_ts()) }}, 9999)
        > {{ var('freshness_alert_hours') }}                  as is_stale
from latest l
left join last_success s    on s.resource = l.resource
left join recent_failures f on f.resource = l.resource
where l.rn = 1
