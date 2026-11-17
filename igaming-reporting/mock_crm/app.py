"""
Mock CRM / player-account-platform API.

Deliberately behaves like a real vendor API so the ingestion code has to handle it:
  * bearer-token auth
  * cursor pagination with a page-size cap
  * incremental pulls via `updated_since`
  * occasional HTTP 429 rate limiting (with Retry-After)
  * records repeated across pages (so the warehouse must deduplicate)

Swap this for the operator's real platform API by editing ingestion/endpoints.py only.
"""
import json
import os
import random
from pathlib import Path

from flask import Flask, abort, jsonify, request

DATA = Path(os.environ.get("MOCK_DATA_DIR", Path(__file__).parent / "data"))
TOKEN = os.environ.get("MOCK_API_TOKEN", "local-dev-token")
RATE_LIMIT_PROB = float(os.environ.get("MOCK_RATE_LIMIT_PROB", "0.03"))
MAX_PAGE = 1000

app = Flask(__name__)
_cache = {}

RESOURCES = {
    "players": "updated_at",
    "transactions": "updated_at",
    "bets": "updated_at",
    "bonus-events": "event_at",
}


def load(name):
    if name not in _cache:
        rows = json.loads((DATA / f"{name.replace('-', '_')}.json").read_text())
        _cache[name] = rows
    return _cache[name]


@app.get("/health")
def health():
    return jsonify(status="ok")


@app.before_request
def auth():
    if request.path == "/health":
        return None
    if request.headers.get("Authorization") != f"Bearer {TOKEN}":
        abort(401)
    if random.random() < RATE_LIMIT_PROB:
        resp = jsonify(error="rate_limited")
        resp.status_code = 429
        resp.headers["Retry-After"] = "1"
        return resp


@app.get("/v1/<resource>")
def list_resource(resource):
    if resource not in RESOURCES:
        abort(404)
    ts_field = RESOURCES[resource]
    since = request.args.get("updated_since", "1970-01-01T00:00:00Z")
    limit = min(int(request.args.get("limit", 500)), MAX_PAGE)
    cursor = int(request.args.get("cursor", 0))

    rows = sorted((r for r in load(resource) if r[ts_field] >= since), key=lambda r: r[ts_field])
    page = rows[cursor:cursor + limit]
    # Real APIs often repeat the boundary record when timestamps tie: simulate it.
    if cursor > 0 and page:
        page = [rows[cursor - 1]] + page
    nxt = cursor + limit
    return jsonify(data=page, next_cursor=nxt if nxt < len(rows) else None, total=len(rows))


@app.get("/v1/reports/daily-summary")
def daily_summary():
    frm = request.args.get("from", "1970-01-01")
    to = request.args.get("to", "9999-12-31")
    return jsonify(data=[r for r in load("daily_summary") if frm <= r["report_date"] <= to])


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", 8765)))
