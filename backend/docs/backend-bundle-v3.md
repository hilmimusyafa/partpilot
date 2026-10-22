# PartPilot Backend Bundle v3 (WO v2 Ancestry + Cross-Warehouse Availability + Downtime Economics)

## 1. System Overview
Backend Bundle v3 combines:
1. **Work Order v2 Ancestry:** Canonical AC hierarchy (`company -> site -> production_line -> station -> machine`).
2. **Read-Only Availability Evaluation (`POST /api/v1/availability/evaluate`):** Synchronous cross-warehouse inventory availability with origin-first shortcut, per-scope catalog note allowlists, exact cross-warehouse label matching, and zero stock reservation.
3. **Deterministic Economic Disruption Calculator (`POST /api/v1/disruption/evaluate`):** High-precision Decimal partial capacity loss calculator, parallel stage DAG restore scheduling, operating window clipping, and non-duplicated cost categorization.

## 2. Component Design

### Availability (`backend.wo.availability`)
- Reads identified session in read-only transaction.
- Evaluates origin warehouse stock first: `available = max(actual - reserved, 0)`. If sufficient, returns `status = fulfilled_source` with `alternatives = []`.
- If origin insufficient/absent, enumerates active leaf warehouses within same company (max 100+1).
- Scopes each warehouse note independently; requires exact brand + base + suffix evidence.
- Flags shortages `max(requested - available, 0)`.

### Downtime Economics (`backend.wo.economics`)
- Stateless deterministic calculator operating at Decimal precision 50.
- Wire decimal strings required (rejects floats, NaN, Inf).
- Partial capacity loss formula:
  - `lost_output = (normal_output_per_hour - disrupted_output_per_hour) * effective_scheduled_impacted_hours`
  - `unit_contribution_margin = net_selling_price_per_unit - avoidable_variable_cost_per_unit`
  - `unrecoverable_lost_contribution = lost_output * (1 - recoverable_fraction) * unit_contribution_margin`
  - `estimated_economic_disruption = unrecoverable_lost_contribution + sum(incremental_disruption_costs)`
  - `future_relevant_option_total = sum(sourcing_costs) + estimated_economic_disruption`
- DAG schedule verification across all 5 required stages (`procurement`, `dispatch`, `transport`, `installation`, `restart`).
- Parallel restore: `restore_at = max(stage ends)`.
- Operating window clipping: loss window clipped to `[future_from, min(restore_at, horizon_end)]` intersected with scheduled operating windows.
- Sourcing vs incremental disruption cost buckets with non-duplication attestations.

### AI Runtime Gateway Adapter (`backend.wo.gateway`)
- Real product adapter communicating with 9router (`http://127.0.0.1:20128/v1`) using `ag/gemini-3.8-flash-high`.
- Complete secret redaction across headers and logs.

## 3. Verification Evidence
Executed in isolated test-owned PostgreSQL 16 environment:
- `bundle-v3-acceptance-suite`:
  ```bash
  /srv/hermes-control/services/partpilot/.venv/bin/python private/bundle-v3/run_acceptance.py test
  ```
  Result: 35 passed, 0 failed, 0 errors in ~8.4s. Exit code: 0.
- `bundle-v3-runtime-gateway-adapter`:
  ```bash
  /srv/hermes-control/services/partpilot/.venv/bin/python private/bundle-v3/run_live_check.py
  ```
  Result: status PASSED, response time ~4.7s. Exit code: 0.
