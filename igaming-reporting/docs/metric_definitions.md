# Metric definitions

All money in ZAR. All dates are reporting days in SAST (UTC+2). These are the defaults in this
build; **every definition is confirmed with the operator's finance team during discovery** and the
configurable parts live in `dbt/dbt_project.yml` vars.

| Metric | Definition | Date basis |
|---|---|---|
| Registrations | New player accounts | Registration date |
| FTDs | Players making their first ever completed deposit | First deposit date |
| FTD amount | Value of those first deposits | First deposit date |
| Deposits | Sum of **completed** deposits (failed/pending excluded) | Deposit created date |
| Withdrawals | Sum of **completed** withdrawals | Withdrawal created date |
| Net deposits | Deposits − withdrawals | |
| Depositors | Distinct players with ≥1 completed deposit | |
| Turnover (handle) | Total settled stakes, cash + bonus | Settlement date |
| Payouts | Total winnings paid on settled bets | Settlement date |
| **GGR** | Turnover − payouts. Also split into casino and sportsbook | Settlement date |
| Hold % | GGR ÷ turnover (calculated over sums, never averaged) | |
| Bonus granted | Bonus value awarded (informational, not a cost) | Grant date |
| **Bonus cost** | Bonus money converted into withdrawable cash (`bonus_cost_event_types`, default `released`) | Release date |
| **NGR** | GGR − bonus cost − gambling levy − VAT (`gambling_levy_rate`, `vat_fraction_of_ggr`, default 0) | |
| Active players | Distinct players with ≥1 settled bet | Settlement date |

## Questions to settle with finance in discovery

- Is GGR reported on cash stakes only, or cash + bonus stakes?
- Which bonus events are a cost (released, wagered, free-bet winnings)? Are forfeited bonuses netted?
- NGR deductions: provincial levy rate(s) per licence, VAT treatment, payment fees, affiliate costs?
- Are voided/cancelled bets excluded or reversed?
- Which back-office report is the "source of truth" to reconcile against, and when is a day considered closed?
