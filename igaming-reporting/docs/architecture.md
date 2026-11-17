# Architecture

## Run sequence (each scheduled execution)

1. **Cloud Scheduler** triggers the **Cloud Run Job** on the agreed cadence (hourly by default; daily or every 15 minutes are a one-line change in `deploy/setup_gcp.sh`).
2. **Ingestion** (`ingestion/main.py`) loads each resource as its own batch:
   - reads the last successful watermark for the resource from `ops.load_audit`
   - requests records updated since `watermark − LOOKBACK_MINUTES` (overlap catches late updates)
   - applies POPIA rules (`ingestion/pii.py`) before anything is written
   - appends to `raw_crm.<resource>` with `_batch_id` and `_loaded_at`
   - writes a success/failure row to `ops.load_audit` (the watermark only moves on success)
   - pulls the platform's own daily summary report for the last N days for reconciliation
3. **dbt build** runs all models and tests in dependency order. Tests include reconciliation, so bad figures fail the run.
4. **Health checks** (`monitoring/check_and_alert.py`) read dbt results, `ops_load_health` and `ops_reconciliation`, then alert if anything is wrong.

A failure in one step doesn't stop later steps, so a failed load still produces an alert, and existing dashboard tables are only replaced by a successful dbt build.

## Datasets

| Dataset | Contents | Who can read |
|---|---|---|
| `raw_crm` | Landed API data (PII already minimised), append-only | Pipeline service account, data admins |
| `ops` | `load_audit` | Pipeline, data admins |
| `staging`, `intermediate` | Views: deduped, typed, SAST dates | Pipeline, data admins |
| `marts` | Dimensions and facts | Analysts |
| `reporting` | Looker Studio sources | Business report users |
| `ops_reporting` | Reconciliation and load health | Report users (Data Health page) |

## Refresh cadence options

| Cadence | How | Notes |
|---|---|---|
| Daily | Scheduler `0 5 * * *` | Lowest cost; dashboards show up to yesterday |
| Hourly (default) | Scheduler `0 * * * *` | Intraday view; incremental pulls keep it cheap |
| Near real-time | Scheduler every 5–15 min + incremental dbt models | Needs the platform API rate limits to allow it; convert large facts to `incremental` materialisation |

## Cost notes

At typical mid-size operator volumes, BigQuery storage and query costs for this design are modest. The main levers are partitioning (`fct_player_daily`, `rpt_player_activity_daily` are date-partitioned and clustered), incremental models at higher refresh frequencies, and Looker Studio's data freshness cache setting. Running costs are billed to the operator's project.
