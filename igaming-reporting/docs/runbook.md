# Runbook

## When an alert arrives

The alert names the problem. Find it below.

### "Load problem: <resource> ..."
1. Open Cloud Run → Jobs → `igaming-reporting-pipeline` → latest execution → Logs.
2. Common causes: expired/rotated API token (HTTP 401 → update secret `crm-api-token`), platform API outage (5xx, usually self-heals on the next run), rate limiting.
3. No manual backfill is needed: the watermark didn't advance, so the next successful run re-pulls the gap. To force a run now: `gcloud run jobs execute igaming-reporting-pipeline --region=africa-south1`.

### "Reconciliation mismatch <date> <metric> ..."
1. Open the Data Health page or query `ops_reporting.ops_reconciliation where status = 'mismatch'`.
2. If the platform restated a day (late settlements, corrections), the next run pulls the updated report and the mismatch clears on its own.
3. If it persists: compare the raw records for that day with the platform's back office. Check `ops.load_audit` for gaps around that time. A missing window can be re-pulled by deleting the affected `load_audit` success rows for that resource so the watermark moves back.

### "dbt fail / error: <model or test>"
1. Run locally against prod: `cd dbt && dbt build --target prod --select <model>+`.
2. Schema change from the platform (new/renamed field) is the usual cause: update `ingestion/endpoints.py` and the staging model.

## Routine

| Task | How |
|---|---|
| Change refresh frequency | `gcloud scheduler jobs update http igaming-reporting-pipeline-trigger --schedule="..."` |
| Rotate API token | `gcloud secrets versions add crm-api-token --data-file=-` |
| Change metric definition | Edit `dbt/dbt_project.yml` vars or `macros/metrics.sql`, open a pull request, deploy |
| Grant a new report user | Add them to the reporting Google Group |
| Full rebuild of models | `dbt build --target prod --full-refresh` |
