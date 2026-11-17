"""All runtime config comes from environment variables (set on the Cloud Function / Cloud Run job).
Secrets (API token, PII hashing key) are read from Secret Manager in production."""
import os
from dataclasses import dataclass


def _secret(name: str, default: str | None = None) -> str | None:
    """Env var first (local dev), then Google Secret Manager (production)."""
    if os.environ.get(name):
        return os.environ[name]
    project = os.environ.get("GCP_PROJECT")
    if project and os.environ.get("USE_SECRET_MANAGER", "true").lower() == "true":
        from google.cloud import secretmanager  # imported lazily so local runs don't need it
        client = secretmanager.SecretManagerServiceClient()
        path = f"projects/{project}/secrets/{name.lower().replace('_', '-')}/versions/latest"
        return client.access_secret_version(name=path).payload.data.decode()
    return default


@dataclass(frozen=True)
class Settings:
    api_base_url: str
    api_token: str
    pii_hash_key: str
    warehouse: str                 # "bigquery" | "duckdb"
    gcp_project: str | None
    raw_dataset: str
    ops_dataset: str
    duckdb_path: str
    page_size: int
    lookback_minutes: int          # re-pull overlap to catch late-arriving updates
    summary_lookback_days: int


def load_settings() -> Settings:
    return Settings(
        api_base_url=os.environ.get("CRM_API_BASE_URL", "http://127.0.0.1:8765"),
        api_token=_secret("CRM_API_TOKEN", "local-dev-token"),
        pii_hash_key=_secret("PII_HASH_KEY", "local-dev-only-not-secret"),
        warehouse=os.environ.get("WAREHOUSE", "duckdb"),
        gcp_project=os.environ.get("GCP_PROJECT"),
        raw_dataset=os.environ.get("RAW_DATASET", "raw_crm"),
        ops_dataset=os.environ.get("OPS_DATASET", "ops"),
        duckdb_path=os.environ.get("DUCKDB_PATH", "warehouse.duckdb"),
        page_size=int(os.environ.get("PAGE_SIZE", "1000")),
        lookback_minutes=int(os.environ.get("LOOKBACK_MINUTES", "180")),
        summary_lookback_days=int(os.environ.get("SUMMARY_LOOKBACK_DAYS", "7")),
    )
