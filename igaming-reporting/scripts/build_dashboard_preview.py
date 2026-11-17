"""
Build docs/dashboard_preview.html: a static preview of the Looker Studio report pages,
generated from the local warehouse. Useful for screenshots and for agreeing the layout
with stakeholders before building it in Looker Studio.
"""
import json
import os
from decimal import Decimal
from pathlib import Path

import duckdb

con = duckdb.connect(os.environ.get("DUCKDB_PATH", "warehouse.duckdb"), read_only=True)


def q(sql):
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    out = []
    for r in cur.fetchall():
        out.append({c: (float(v) if isinstance(v, Decimal) else (v.isoformat() if hasattr(v, "isoformat") else v))
                    for c, v in zip(cols, r)})
    return out


data = {
    "daily": q("""select * from reporting.rpt_daily_kpis
                  where report_date > (select max(report_date) from reporting.rpt_daily_kpis) - 30
                    and report_date < (select max(report_date) from reporting.rpt_daily_kpis)
                  order by report_date"""),
    "province": q("""select province, sum(ggr) ggr, sum(deposits) deposits,
                            count(distinct case when is_active then player_id end) players
                     from reporting.rpt_player_activity_daily
                     where activity_date > (select max(activity_date) from reporting.rpt_player_activity_daily) - 30
                     group by 1 order by ggr desc"""),
    "segment": q("""select value_segment, sum(ngr) ngr, count(distinct player_id) players
                    from reporting.rpt_player_activity_daily
                    where activity_date > (select max(activity_date) from reporting.rpt_player_activity_daily) - 30
                    group by 1 order by ngr desc"""),
    "cohorts": q("""select strftime(ftd_cohort, '%Y-%m') cohort, months_since_ftd m, cohort_players n,
                           round(100.0 * active_players / cohort_players, 1) pct
                    from reporting.rpt_ftd_cohorts order by 1, 2"""),
    "recon": q("""select metric, count(*) filter (where status='match') matched,
                         count(*) filter (where status='mismatch') mismatched,
                         max(abs(difference)) max_diff
                  from ops_reporting.ops_reconciliation group by 1 order by 1"""),
    "loads": q("""select resource, last_status, round(hours_since_success, 2) hours_since_success,
                         failures_24h, is_stale from ops_reporting.ops_load_health order by 1"""),
}

html = Path(__file__).with_name("dashboard_template.html").read_text()
out = Path(os.environ.get("PREVIEW_OUT", "docs/dashboard_preview.html"))
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(html.replace("/*__DATA__*/null", json.dumps(data)))
print(f"Wrote {out} ({len(data['daily'])} days)")
