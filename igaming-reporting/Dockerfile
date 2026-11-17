# One image for the scheduled Cloud Run Job: ingestion -> dbt build -> checks/alerts.
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 WAREHOUSE=bigquery DBT_TARGET=prod
COPY ingestion/requirements.txt ingestion/requirements.txt
RUN pip install --no-cache-dir -r ingestion/requirements.txt "dbt-bigquery>=1.9,<2"
COPY ingestion ingestion
COPY monitoring monitoring
COPY dbt dbt
COPY pipeline.py .
RUN cd dbt && dbt deps --profiles-dir . || true
# Runs as a dedicated, least-privilege service account (no key files in the image).
CMD ["python", "pipeline.py"]
