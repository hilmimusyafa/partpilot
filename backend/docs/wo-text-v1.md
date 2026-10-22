# PartPilot Work Order (WO) Text Identification v2 with Production Ancestry

## Overview
This document describes the implemented Work Order (WO) text identification backend service (v2).
It implements bounded, deterministic identification of replacement parts (initially bearings) from unstructured textual descriptions and confirmed voice transcripts, anchored in AC production line ancestry context (`company -> site -> production_line -> station -> machine`).

## Architectural Scope & Boundaries
- **Controlled-Local MVP:** Bound to loopback `127.0.0.1`. Unverified caller labels confer no authentication or org privileges.
- **Production Hierarchy:** Canonical ancestry is `site -> production_line -> station -> machine` (`erp.asset.name`). Lines must be scoped `AC`.
- **Draft & Submit Semantics:** Incomplete drafts are permitted without AI calls or background jobs. Submissions strictly require complete, valid ancestry and positive quantity.
- **Knowledge Boundary:** Scoped per-warehouse static allowlist (`SYN-WH-01` .. `SYN-WH-05`) with pinned SHA-256 hashes.
- **Deterministic Matching:** Exact item code, full label evidence (`brand + base + suffix`), or <=3 rounds of <=3 discriminating questions. Dimensions-only cannot prove identity.

## API Endpoints
- `POST /api/v1/work-orders`: Create draft session with `Idempotency-Key`
- `PATCH /api/v1/work-orders/{id}`: Update draft session
- `GET /api/v1/work-orders/{id}`: Retrieve session status and findings
- `POST /api/v1/work-orders/{id}/submit`: Submit session for background matching
- `POST /api/v1/work-orders/{id}/answers`: Submit clarification answers
- `POST /api/v1/work-orders/{id}/retry`: Retry failed retriable session
- Reference hierarchy endpoints: `/companies`, `/sites`, `/production-lines`, `/stations`, `/machines`, `/warehouses`

## Test Execution
Tested against isolated PostgreSQL 16 `partpilot_test`:
```bash
/srv/hermes-control/services/partpilot/.venv/bin/python private/bundle-v3/run_acceptance.py test
```
All 35 acceptance tests (A01-A16, H01-H07, V01-V05, E01-E05, B01-B02) pass.
