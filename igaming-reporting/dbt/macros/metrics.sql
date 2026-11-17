{# Single definition of NGR used everywhere, so dashboards can never disagree.
   NGR = GGR - bonus cost - gambling levy - VAT  (rates in dbt_project.yml vars) #}
{% macro ngr(ggr, bonus_cost) -%}
    {%- set expr -%}
        ({{ ggr }} - {{ bonus_cost }}
            - {{ ggr }} * {{ var('gambling_levy_rate') }}
            - {{ ggr }} * {{ var('vat_fraction_of_ggr') }})
    {%- endset -%}
    {{ money(expr) }}
{%- endmacro %}
