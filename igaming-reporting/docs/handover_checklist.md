# Handover checklist

- [ ] Code repository transferred to the operator's GitHub/GitLab organisation; contractor access removed
- [ ] All resources confirmed in the operator's GCP project and billing account
- [ ] Secrets created and populated by the operator (API token, PII hash key, alert webhook)
- [ ] Contractor IAM access to the GCP project removed
- [ ] Metric definitions signed off by finance (`docs/metric_definitions.md`)
- [ ] 14 consecutive days of clean reconciliation against the platform report
- [ ] Alerts tested end to end (`make demo-mismatch` locally; a forced failure in prod) and received by the right people
- [ ] Looker Studio reports owned by an operator account (not the contractor's)
- [ ] Reporting Google Group created and access granted to `reporting` dataset only
- [ ] Walkthrough session recorded: architecture, building a report, responding to each alert type
- [ ] Runbook reviewed with the person on call
