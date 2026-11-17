"""
Single orchestrated run:  ingest  ->  dbt build (models + tests)  ->  health checks / alerts.

Runs as a Cloud Run Job triggered by Cloud Scheduler (see deploy/). Each step runs even if an
earlier one failed, so a failed load still produces an alert and yesterday's good data stays
in the dashboards rather than being half-overwritten.
"""
import logging
import os
import subprocess
import sys

from ingestion.main import run as run_ingestion
from monitoring.check_and_alert import main as run_checks

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("pipeline")


def main() -> int:
    ok = True
    try:
        run_ingestion()
    except Exception:
        log.exception("Ingestion had failures (recorded in ops.load_audit)")
        ok = False

    dbt = subprocess.run(
        ["dbt", "build", "--profiles-dir", ".", "--target", os.environ.get("DBT_TARGET", "local")],
        cwd="dbt",
    )
    ok = ok and dbt.returncode == 0

    alert_code = run_checks("dbt/target")
    return 0 if ok and alert_code == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
