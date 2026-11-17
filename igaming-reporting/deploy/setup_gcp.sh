#!/usr/bin/env bash
# One-time setup in the OPERATOR'S Google Cloud project. Idempotent: safe to re-run.
# Everything (data, code, secrets, service accounts) lives in their project and is owned by them.
#
#   PROJECT_ID=operator-reporting ALERT_EMAIL=data-team@operator.co.za ./deploy/setup_gcp.sh
set -euo pipefail

: "${PROJECT_ID:?set PROJECT_ID}"
: "${ALERT_EMAIL:?set ALERT_EMAIL}"
REGION="${REGION:-africa-south1}"            # Johannesburg: player data stays in South Africa
SCHEDULE="${SCHEDULE:-0 * * * *}"            # hourly; daily = "0 5 * * *" (SAST timezone below)
JOB=igaming-reporting-pipeline
SA_RUN="pipeline-runner@${PROJECT_ID}.iam.gserviceaccount.com"
SA_SCHED="pipeline-scheduler@${PROJECT_ID}.iam.gserviceaccount.com"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/reporting/pipeline:$(git rev-parse --short HEAD 2>/dev/null || echo latest)"

gcloud config set project "$PROJECT_ID"

echo "== Enable APIs"
gcloud services enable bigquery.googleapis.com run.googleapis.com cloudscheduler.googleapis.com \
  secretmanager.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com \
  monitoring.googleapis.com logging.googleapis.com

echo "== BigQuery datasets (layered: raw is restricted, reporting is what Looker Studio reads)"
for ds in raw_crm ops staging intermediate marts reporting ops_reporting analytics; do
  bq --location="$REGION" mk -d --if_not_exists=true "${PROJECT_ID}:${ds}" >/dev/null 2>&1 || true
done

echo "== Service accounts (least privilege)"
gcloud iam service-accounts create pipeline-runner --display-name="Reporting pipeline runner" 2>/dev/null || true
gcloud iam service-accounts create pipeline-scheduler --display-name="Reporting pipeline scheduler" 2>/dev/null || true
for role in roles/bigquery.dataEditor roles/bigquery.jobUser roles/secretmanager.secretAccessor roles/logging.logWriter; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:${SA_RUN}" --role="$role" --condition=None >/dev/null
done

echo "== Secrets (values are added by the operator, never committed or emailed)"
for s in crm-api-token pii-hash-key alert-webhook-url; do
  gcloud secrets create "$s" --replication-policy=user-managed --locations="$REGION" 2>/dev/null || true
done
echo "   Add values with:  printf '%s' 'VALUE' | gcloud secrets versions add crm-api-token --data-file=-"
echo "   Generate the PII key with:  openssl rand -hex 32 | gcloud secrets versions add pii-hash-key --data-file=-"

echo "== Build image"
gcloud artifacts repositories create reporting --repository-format=docker --location="$REGION" 2>/dev/null || true
gcloud builds submit --tag "$IMAGE" .

echo "== Cloud Run Job"
gcloud run jobs deploy "$JOB" --image="$IMAGE" --region="$REGION" --service-account="$SA_RUN" \
  --task-timeout=3600 --max-retries=1 --memory=2Gi --cpu=1 \
  --set-env-vars="GCP_PROJECT=${PROJECT_ID},WAREHOUSE=bigquery,DBT_TARGET=prod,ENVIRONMENT=prod,CRM_API_BASE_URL=${CRM_API_BASE_URL:-https://REPLACE-ME}" \
  --set-secrets="CRM_API_TOKEN=crm-api-token:latest,PII_HASH_KEY=pii-hash-key:latest,ALERT_WEBHOOK_URL=alert-webhook-url:latest"

echo "== Cloud Scheduler"
gcloud run jobs add-iam-policy-binding "$JOB" --region="$REGION" \
  --member="serviceAccount:${SA_SCHED}" --role=roles/run.invoker >/dev/null
gcloud scheduler jobs create http "${JOB}-trigger" --location="$REGION" --schedule="$SCHEDULE" \
  --time-zone="Africa/Johannesburg" \
  --uri="https://run.googleapis.com/v2/projects/${PROJECT_ID}/locations/${REGION}/jobs/${JOB}:run" \
  --http-method=POST --oauth-service-account-email="$SA_SCHED" 2>/dev/null \
|| gcloud scheduler jobs update http "${JOB}-trigger" --location="$REGION" --schedule="$SCHEDULE"

echo "== Alerting: email on pipeline alert logs or failed job executions"
CHANNEL=$(gcloud beta monitoring channels create --display-name="Reporting alerts" --type=email \
  --channel-labels=email_address="$ALERT_EMAIL" --format="value(name)")
sed "s#__CHANNEL__#${CHANNEL}#g" deploy/alert_policy.json > /tmp/alert_policy.json
gcloud alpha monitoring policies create --policy-from-file=/tmp/alert_policy.json

echo "Done. Trigger a first run:  gcloud run jobs execute $JOB --region=$REGION"
