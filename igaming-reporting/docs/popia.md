# POPIA: how player data is handled

This describes the technical controls in the pipeline. It supports, but doesn't replace, the
operator's own POPIA compliance process and Information Officer sign-off.

**Minimality (s10).** Reporting doesn't need to identify people, so direct identifiers never enter
the warehouse. Names and SA ID numbers are dropped at ingestion. Email and mobile are stored only as
keyed HMAC-SHA256 hashes (for de-duplication and matching), and date of birth is reduced to birth
year then age band. Rules live in `ingestion/endpoints.py`, and a unit test fails if the platform
starts sending new player fields that aren't explicitly declared.

**Pseudonymisation.** The hash key lives in Secret Manager in the operator's project. Without it,
hashes can't be reversed or recomputed, and rotating it unlinks historical hashes.

**Security safeguards (s19).** Data stays in the operator's Google Cloud project in
`africa-south1` (Johannesburg). The pipeline runs as a dedicated service account with only the
roles it needs; no service-account key files exist. Business users get read access to the
`reporting` dataset only (`deploy/grant_reporting_access.sql`), never raw tables. Credentials are
held in Secret Manager, never in code or the repository.

**Self-excluded and closed accounts.** Account status is carried through so reports and any
marketing extracts can exclude them.

**Retention.** Recommend agreeing a retention period for raw tables and setting BigQuery partition
expiration on `raw_crm` accordingly.

**Contractor access.** During the build the developer works under NDA with access granted by the
operator, scoped to this project, and removed at handover (see handover checklist).
