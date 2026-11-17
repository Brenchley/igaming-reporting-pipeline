{# Convert a UTC timestamp to the operator's reporting date (SAST). #}
{% macro to_local_date(col) -%}
    {{ return(adapter.dispatch('to_local_date')(col)) }}
{%- endmacro %}

{% macro bigquery__to_local_date(col) -%}
    date({{ col }}, '{{ var("reporting_timezone") }}')
{%- endmacro %}

{% macro default__to_local_date(col) -%}
    cast({{ col }} + interval '{{ var("utc_offset_hours") }} hours' as date)
{%- endmacro %}

{# Money type: NUMERIC in BigQuery (exact), DECIMAL elsewhere. Never FLOAT for money. #}
{% macro money(col) -%}
    {{ return(adapter.dispatch('money')(col)) }}
{%- endmacro %}
{% macro bigquery__money(col) -%} cast({{ col }} as numeric) {%- endmacro %}
{% macro default__money(col) -%} cast({{ col }} as decimal(18, 2)) {%- endmacro %}

{% macro safe_divide(num, den) -%}
    case when {{ den }} = 0 or {{ den }} is null then null else {{ num }} / {{ den }} end
{%- endmacro %}

{% macro hours_between(start_ts, end_ts) -%}
    {{ return(adapter.dispatch('hours_between')(start_ts, end_ts)) }}
{%- endmacro %}
{% macro bigquery__hours_between(start_ts, end_ts) -%}
    timestamp_diff({{ end_ts }}, {{ start_ts }}, minute) / 60.0
{%- endmacro %}
{% macro default__hours_between(start_ts, end_ts) -%}
    date_diff('minute', {{ start_ts }}, {{ end_ts }}) / 60.0
{%- endmacro %}

{% macro current_ts() -%}
    {{ return(adapter.dispatch('current_ts')()) }}
{%- endmacro %}
{% macro bigquery__current_ts() -%} current_timestamp() {%- endmacro %}
{% macro default__current_ts() -%} cast(now() at time zone 'UTC' as timestamp) {%- endmacro %}

{% macro ts_hours_ago(n) -%}
    {{ return(adapter.dispatch('ts_hours_ago')(n)) }}
{%- endmacro %}
{% macro bigquery__ts_hours_ago(n) -%} timestamp_sub(current_timestamp(), interval {{ n }} hour) {%- endmacro %}
{% macro default__ts_hours_ago(n) -%} ({{ current_ts() }} - interval '{{ n }} hours') {%- endmacro %}

{# Today's date in SAST minus n days. #}
{% macro local_days_ago(n) -%}
    {{ return(adapter.dispatch('local_days_ago')(n)) }}
{%- endmacro %}
{% macro bigquery__local_days_ago(n) -%}
    date_sub(current_date('{{ var("reporting_timezone") }}'), interval {{ n }} day)
{%- endmacro %}
{% macro default__local_days_ago(n) -%}
    ({{ to_local_date(current_ts()) }} - {{ n }})
{%- endmacro %}
