# Adapting to the operator's platform API

The mock API in `mock_crm/` stands in for the operator's real player-account / CRM platform.
Pointing the pipeline at the real one is deliberately contained:

1. **Discovery (with API docs under NDA):** list the resources needed (players, payments, bets/rounds, bonuses), their pagination style, incremental filter field, rate limits, and whether the platform exposes a daily summary or GGR report to reconcile against.
2. **`ingestion/endpoints.py`:** set the path, primary key, watermark field and columns for each resource, and the PII rule for every personal field.
3. **`ingestion/client.py`:** only if pagination or auth differ (e.g. page numbers instead of cursors, OAuth client-credentials instead of a bearer token).
4. **Staging models:** map the platform's field names and status codes (e.g. its bet and transaction statuses) to the standard ones used downstream. Marts, reporting tables, tests and dashboards don't change.
5. **Reconciliation:** map the platform's own report fields in `stg_crm__daily_summary`. If no API report exists, a scheduled CSV export from the back office into a GCS bucket works as the reconciliation source.

If the platform offers bulk exports or a data feed in addition to the REST API, those are often a better fit for high-volume tables such as bets/game rounds; the raw contract stays the same.
