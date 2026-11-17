{# Use the configured schema name as-is (raw_crm, staging, marts, reporting...) rather than
   dbt's default <target>_<schema>, so Looker Studio data sources point at stable datasets. #}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}{{ target.schema }}{%- else -%}{{ custom_schema_name | trim }}{%- endif -%}
{%- endmacro %}
