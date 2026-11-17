-- FAILS if the core accounting identities break on any day.
select report_date, 'ggr != turnover - payouts' as problem
from {{ ref('fct_daily_kpis') }}
where abs(ggr - (turnover - payouts)) > 0.01
union all
select report_date, 'ggr != casino + sportsbook'
from {{ ref('fct_daily_kpis') }}
where abs(ggr - (casino_ggr + sportsbook_ggr)) > 0.01
union all
select report_date, 'negative deposits'
from {{ ref('fct_daily_kpis') }}
where deposits < 0
union all
select report_date, 'more FTDs than depositors'
from {{ ref('fct_daily_kpis') }}
where ftd_count > depositors
