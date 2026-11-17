"""
Ingestion entrypoint.

  Cloud Function (HTTP, triggered by Cloud Scheduler):  ingest(request)
  Local / CLI:                                            python -m ingestion.main [resource ...]

Each resource load is one batch, recorded in ops.load_audit whether it succeeds or fails.
The incremental watermark only advances on success, so a failed run is re-pulled next time.
"""
import json
import logging
import sys
import uuid
from datetime import date, datetime, timedelta, timezone

from . import endpoints
from .client import CrmClient
from .config import load_settings
from .pii import apply_pii_rules
from .warehouse import AUDIT_COLUMNS, META_COLUMNS, get_warehouse, utcnow

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ingestion")


def _shift(ts: str, minutes: int) -> str:
    dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return (dt - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_resource(ep, client, wh, s) -> dict:
    batch_id = str(uuid.uuid4())
    audit = {"batch_id": batch_id, "resource": ep.name, "started_at": utcnow(), "status": "running",
             "rows_loaded": 0, "watermark_from": None, "watermark_to": None, "error": None}
    table_cols = {**ep.columns, **META_COLUMNS}
    wh.ensure_table(s.raw_dataset, ep.name, table_cols)
    try:
        loaded_at = utcnow()
        if ep.incremental:
            prev = wh.last_watermark(s.ops_dataset, ep.name)
            since = _shift(prev, s.lookback_minutes) if prev else None
            audit["watermark_from"] = since
            max_wm, total = prev, 0
            for page in client.paginate(ep.path, updated_since=since):
                rows = []
                for rec in page:
                    rec = apply_pii_rules(rec, ep.pii, s.pii_hash_key)
                    rec.update(_batch_id=batch_id, _loaded_at=loaded_at)
                    rows.append(rec)
                    wm = rec.get(ep.watermark_field)
                    if wm and (max_wm is None or wm > max_wm):
                        max_wm = wm
                total += wh.append(s.raw_dataset, ep.name, table_cols, rows)
            audit["watermark_to"] = max_wm
        else:
            frm = (date.today() - timedelta(days=s.summary_lookback_days)).isoformat()
            rows = client.get_report(ep.path, **{"from": frm})
            for r in rows:
                r.update(_batch_id=batch_id, _loaded_at=loaded_at)
            total = wh.append(s.raw_dataset, ep.name, table_cols, rows)
            audit["watermark_from"], audit["watermark_to"] = frm, date.today().isoformat()
        audit.update(status="success", rows_loaded=total)
        log.info("Loaded %s: %s rows (batch %s)", ep.name, total, batch_id)
    except Exception as exc:  # recorded, then re-raised so the run is reported as failed
        audit.update(status="failed", error=f"{type(exc).__name__}: {exc}"[:1000])
        log.exception("Load failed for %s", ep.name)
    finally:
        audit["finished_at"] = utcnow()
        wh.append(s.ops_dataset, "load_audit", AUDIT_COLUMNS, [audit])
    return audit


def run(resource_names=None) -> list[dict]:
    s = load_settings()
    wh = get_warehouse(s)
    wh.ensure_table(s.ops_dataset, "load_audit", AUDIT_COLUMNS)
    client = CrmClient(s.api_base_url, s.api_token, s.page_size)
    names = resource_names or list(endpoints.ALL)
    results = [load_resource(endpoints.ALL[n], client, wh, s) for n in names]
    if any(r["status"] == "failed" for r in results):
        raise RuntimeError(json.dumps([r for r in results if r["status"] == "failed"], default=str))
    return results


def ingest(request):
    """Cloud Function HTTP entrypoint. Body (optional): {"resources": ["bets", ...]}"""
    body = request.get_json(silent=True) or {}
    results = run(body.get("resources"))
    return json.dumps(results, default=str), 200, {"Content-Type": "application/json"}


if __name__ == "__main__":
    run(sys.argv[1:] or None)
