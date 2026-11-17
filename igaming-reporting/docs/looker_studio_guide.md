# Looker Studio guide

## Data sources

Connect Looker Studio to these BigQuery tables (dataset `reporting` / `ops_reporting`):

| Data source | Use for |
|---|---|
| `rpt_daily_kpis` | Executive overview: trends, scorecards, period comparisons |
| `rpt_player_activity_daily` | Self-serve: any measure by province, channel, age band, KYC status, value segment, cohort |
| `rpt_ftd_cohorts` | Retention and lifetime value by first-deposit month |
| `ops_reconciliation`, `ops_load_health` | Data Health page |

Column descriptions from dbt are written into BigQuery and appear in Looker Studio's field list.
Set data freshness on each source to match the pipeline schedule (e.g. 1 hour).

## Report pages

1. **Executive overview:** scorecards (deposits, net deposits, turnover, GGR, hold %, bonus cost, NGR, registrations, FTDs), GGR vs NGR trend, deposits vs withdrawals, GGR by product, active players and FTDs. Date range control defaulting to "last 30 days", with comparison to the previous period.
2. **Players and cohorts:** GGR by province, NGR by value segment, FTD cohort retention heatmap.
3. **Data health:** last load per source, hours since success, reconciliation matches/mismatches. Put a "data last validated" scorecard on page 1 too, so readers see at a glance that numbers are trusted.

## Calculated fields (create once in the data source, then reusable everywhere)

Ratios must be calculated from sums, never averaged across rows:

```
Hold %            = SUM(ggr) / SUM(turnover)
Avg deposit       = SUM(deposits) / SUM(deposit_count)
ARPU (NGR)        = SUM(ngr) / COUNT_DISTINCT(CASE WHEN is_active THEN player_id END)   -- player table
Bonus cost % GGR  = SUM(bonus_cost) / SUM(ggr)
FTD conversion    = SUM(ftd_count) / SUM(registrations)
```

Note: `active_players` and `depositors` in `rpt_daily_kpis` are daily distinct counts. Summing them
across a month counts the same player once per day. For monthly unique players use
`COUNT_DISTINCT(player_id)` on `rpt_player_activity_daily`.

## Building a new report without a developer

1. Create a report, add `rpt_player_activity_daily` as the data source.
2. Pick a dimension (e.g. `registration_channel`) and a measure (e.g. `ngr`).
3. Add filters (e.g. `account_status = active`, date range).
4. If a needed attribute isn't in the table, that's the only point to raise a change request: adding a column to the dbt model makes it available to every report.
