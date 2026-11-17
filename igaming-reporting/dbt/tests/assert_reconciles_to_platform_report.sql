-- FAILS if any closed day differs from the platform's own report by more than the tolerance.
-- This is the "can we trust the numbers" gate: the alerting job reports these rows.
select *
from {{ ref('ops_reconciliation') }}
where status = 'mismatch'
