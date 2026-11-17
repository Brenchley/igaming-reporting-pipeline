-- POPIA least-privilege: business users get read access to the REPORTING dataset only.
-- They never see raw_crm, staging or ops tables. Run in the BigQuery console as an admin.
-- Replace the group with the operator's Google Group for report viewers/builders.
GRANT `roles/bigquery.dataViewer`
ON SCHEMA `PROJECT_ID.reporting`
TO "group:reporting-users@operator.co.za";

-- Users building reports in Looker Studio with their own credentials also need to run queries:
--   gcloud projects add-iam-policy-binding PROJECT_ID \
--     --member=group:reporting-users@operator.co.za --role=roles/bigquery.jobUser
