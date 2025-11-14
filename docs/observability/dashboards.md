# Observability Dashboards (Grafana)

Recommended panels and queries (adjust for your metrics backend):

- Transfers & fees funnel
  - Count of `/transfers` by status
  - Sum of `fee_amount` by type (platform/community/federal)

- Contributions (CDF)
  - Sum of `community_contributions.contribution_amount` by community
  - 30d contributions trend

- Reconciliation
  - `settlement_batches` status count (RECONCILED vs VARIANCE)
  - Variance amount (expected vs actual)

- Payout approvals
  - `multisig_approvals` by status (PENDING, APPROVED, EXECUTED)
  - Mean time to approve and execute

- Latency and errors
  - p50/p95 latency for `/transfers`, `/payouts`, `/checkout/initiate`
  - Error rate by route

Implementation tip: instrument request latency and outcomes via your WSGI/gunicorn metrics or add middleware to emit Prometheus metrics.

