"""
Warehouse adapters. Production = BigQuery. Local demo = DuckDB (same raw contract,
so the dbt project and checks run unchanged against either).

Raw tables are append-only: every load adds rows tagged with _batch_id/_loaded_at.
De-duplication happens in dbt staging, which keeps raw history auditable.
"""
import json
import os
import tempfile
from abc import ABC, abstractmethod
from datetime import datetime, timezone

META_COLUMNS = {"_batch_id": "string", "_loaded_at": "timestamp"}

AUDIT_COLUMNS = {
    "batch_id": "string", "resource": "string", "started_at": "timestamp", "finished_at": "timestamp",
    "status": "string", "rows_loaded": "int", "watermark_from": "string", "watermark_to": "string",
    "error": "string",
}


class Warehouse(ABC):
    @abstractmethod
    def ensure_table(self, dataset: str, table: str, columns: dict) -> None: ...

    @abstractmethod
    def append(self, dataset: str, table: str, columns: dict, rows: list[dict]) -> int: ...

    @abstractmethod
    def last_watermark(self, ops_dataset: str, resource: str) -> str | None: ...


class BigQueryWarehouse(Warehouse):
    BQ_TYPES = {"string": "STRING", "int": "INT64", "bool": "BOOL", "money": "NUMERIC",
                "timestamp": "TIMESTAMP", "date": "DATE"}

    def __init__(self, project: str, location: str = "africa-south1"):
        from google.cloud import bigquery
        self.bq = bigquery
        self.client = bigquery.Client(project=project, location=location)
        self.project = project

    def _schema(self, columns):
        return [self.bq.SchemaField(c, self.BQ_TYPES[t]) for c, t in columns.items()]

    def ensure_table(self, dataset, table, columns):
        ref = f"{self.project}.{dataset}.{table}"
        t = self.bq.Table(ref, schema=self._schema(columns))
        if "_loaded_at" in columns:
            t.time_partitioning = self.bq.TimePartitioning(field="_loaded_at")
        self.client.create_table(t, exists_ok=True)

    def append(self, dataset, table, columns, rows):
        if not rows:
            return 0
        cfg = self.bq.LoadJobConfig(schema=self._schema(columns),
                                    write_disposition="WRITE_APPEND",
                                    source_format="NEWLINE_DELIMITED_JSON")
        job = self.client.load_table_from_json(rows, f"{self.project}.{dataset}.{table}", job_config=cfg)
        job.result()  # raises on failure, so the batch is marked failed in the audit log
        return len(rows)

    def last_watermark(self, ops_dataset, resource):
        q = f"""select max(watermark_to) as wm from `{self.project}.{ops_dataset}.load_audit`
                where resource = @r and status = 'success'"""
        cfg = self.bq.QueryJobConfig(query_parameters=[self.bq.ScalarQueryParameter("r", "STRING", resource)])
        rows = list(self.client.query(q, job_config=cfg).result())
        return rows[0].wm if rows else None


class DuckDBWarehouse(Warehouse):
    DUCK_TYPES = {"string": "VARCHAR", "int": "BIGINT", "bool": "BOOLEAN", "money": "DECIMAL(18,2)",
                  "timestamp": "TIMESTAMP", "date": "DATE"}

    def __init__(self, path: str):
        import duckdb
        self.con = duckdb.connect(path)

    def ensure_table(self, dataset, table, columns):
        self.con.execute(f"create schema if not exists {dataset}")
        cols = ", ".join(f'"{c}" {self.DUCK_TYPES[t]}' for c, t in columns.items())
        self.con.execute(f"create table if not exists {dataset}.{table} ({cols})")

    def append(self, dataset, table, columns, rows):
        if not rows:
            return 0
        with tempfile.NamedTemporaryFile("w", suffix=".ndjson", delete=False) as f:
            for r in rows:
                f.write(json.dumps({c: r.get(c) for c in columns}) + "\n")
            path = f.name
        spec = "{" + ", ".join(f"'{c}': '{self.DUCK_TYPES[t]}'" for c, t in columns.items()) + "}"
        self.con.execute(f"insert into {dataset}.{table} select * from read_json('{path}', "
                         f"format='newline_delimited', columns={spec})")
        os.unlink(path)
        return len(rows)

    def last_watermark(self, ops_dataset, resource):
        r = self.con.execute(f"select max(watermark_to) from {ops_dataset}.load_audit "
                             f"where resource = ? and status = 'success'", [resource]).fetchone()
        return r[0] if r else None


def get_warehouse(settings) -> Warehouse:
    if settings.warehouse == "bigquery":
        return BigQueryWarehouse(settings.gcp_project)
    return DuckDBWarehouse(settings.duckdb_path)


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
