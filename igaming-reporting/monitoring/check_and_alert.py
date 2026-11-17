"""
Post-run health checks. Raises an alert when:
  1. any ingestion batch failed, or a resource has had no successful load for too long
  2. any dbt model or test failed (incl. reconciliation tests)
  3. any closed day's figures differ from the platform's own report beyond tolerance

Alerts go to a chat webhook (Slack / Google Chat / Teams incoming webhook: ALERT_WEBHOOK_URL)
and are also written as ERROR-severity structured logs, which a Cloud Monitoring alert policy
turns into email/SMS for on-call. Exit code is non-zero on any alert so the Cloud Run Job
execution is marked failed too (belt and braces).
"""
import json
import logging
import os
import sys
from pathlib import Path

import requests

log = logging.getLogger("monitoring")
MAX_ROWS_IN_MESSAGE = 10


class Queryer:
    def __init__(self):
        self.kind = os.environ.get("WAREHOUSE", "duckdb")
        if self.kind == "bigquery":
            from google.cloud import bigquery
            self.client = bigquery.Client(project=os.environ["GCP_PROJECT"])
            self.prefix = f"`{os.environ['GCP_PROJECT']}`."
        else:
            import duckdb
            self.client = duckdb.connect(os.environ.get("DUCKDB_PATH", "warehouse.duckdb"), read_only=True)
            self.prefix = ""

    def rows(self, sql: str) -> list[dict]:
        sql = sql.replace("{p}", self.prefix)
        if self.kind == "bigquery":
            return [dict(r) for r in self.client.query(sql).result()]
        cur = self.client.execute(sql)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def check_loads(q: Queryer) -> list[str]:
    rows = q.rows("""select resource, last_status, last_error, hours_since_success, failures_24h, is_stale
                     from {p}ops_reporting.ops_load_health
                     where last_status = 'failed' or is_stale""")
    return [f"Load problem: *{r['resource']}* last status={r['last_status']}, "
            f"{r['failures_24h']} failures in 24h, "
            f"{(r['hours_since_success'] or 0):.1f}h since last success. "
            f"Error: {(r['last_error'] or '-')[:200]}" for r in rows]


def check_reconciliation(q: Queryer) -> list[str]:
    rows = q.rows("""select report_date, metric, our_value, platform_value, difference
                     from {p}ops_reporting.ops_reconciliation
                     where status = 'mismatch'
                     order by report_date desc, abs(difference) desc""")
    msgs = [f"Reconciliation mismatch {r['report_date']} *{r['metric']}*: ours R{float(r['our_value']):,.2f} "
            f"vs platform R{float(r['platform_value']):,.2f} (diff R{float(r['difference']):,.2f})"
            for r in rows[:MAX_ROWS_IN_MESSAGE]]
    if len(rows) > MAX_ROWS_IN_MESSAGE:
        msgs.append(f"...and {len(rows) - MAX_ROWS_IN_MESSAGE} more mismatches (see Data Health dashboard).")
    return msgs


def check_dbt(run_results: Path) -> list[str]:
    if not run_results.exists():
        return ["dbt did not produce run_results.json: the transformation step did not run."]
    res = json.loads(run_results.read_text())
    bad = [r for r in res.get("results", []) if r["status"] in ("error", "fail", "runtime error")]
    return [f"dbt {r['status']}: *{r['unique_id'].split('.')[-1]}*: {(r.get('message') or '')[:200]}" for r in bad]


def send(alerts: list[str]) -> None:
    env = os.environ.get("ENVIRONMENT", "local")
    text = f":rotating_light: *iGaming reporting pipeline ({env})*: {len(alerts)} issue(s)\n" + \
           "\n".join(f"• {a}" for a in alerts)
    # Structured log: Cloud Logging picks up `severity`, and the alert policy matches on it.
    print(json.dumps({"severity": "ERROR", "message": text, "alert_type": "reporting_pipeline"}))
    url = os.environ.get("ALERT_WEBHOOK_URL")
    if url:
        try:
            requests.post(url, json={"text": text}, timeout=15).raise_for_status()
        except requests.RequestException:
            log.exception("Webhook delivery failed (alert still logged)")


def main(dbt_target_dir: str = "dbt/target") -> int:
    q = Queryer()
    alerts = check_dbt(Path(dbt_target_dir) / "run_results.json")
    for check in (check_loads, check_reconciliation):
        try:
            alerts += check(q)
        except Exception as exc:  # the check itself failing is an alert too
            alerts.append(f"Health check {check.__name__} could not run: {exc}")
    if alerts:
        send(alerts)
        return 1
    print(json.dumps({"severity": "INFO", "message": "All checks passed: loads fresh, dbt green, figures reconcile."}))
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
