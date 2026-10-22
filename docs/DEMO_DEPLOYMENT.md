# PartPilot integrated bearing demo

Public URL: https://partpilot.rifqisetiawan.my.id

The frontend from main and the backend bearing branch are integrated. The served application uses Next.js static export, FastAPI, PostgreSQL 16 and a separately supervised identification worker. Caddy terminates HTTPS. Only the synthetic demo database is connected. The original ERP connection and original canonical working tree are not overwritten.

## Demo boundaries

- Shared demo login, username `demo`; password stays in the host's scoped runtime file. Role selection on the landing page is navigation, not production RBAC.
- Vendor sourcing offers two separate modes per run: deterministic simulator, or real WhatsApp Web via a private Baileys bridge to opted-in demo recipients. Real delivery is an external side effect; do not describe it as simulated messaging. Manager vendor selection atomically generates an immutable PT PartPilot demo PO; warehouse selection shows a confirmation popup and creates no PO. No real purchase, transfer, reservation or completed repair is executed, and POs are not sent to vendors.
- Five warehouses exist. WH01 and WH02 have documented naming rules. WH03–WH05 remain explicitly unknown, not confirmed empty.
- Reset clears active WO/procurement state and restores seeded stock. Previous workflow rows are archived in immutable `pp.demo_reset_audit`; audit storage grows with resets. Reset affects all people sharing this demo.
- Database checks require an explicitly enabled synthetic dataset marker, matching database identity and no foreign company. Reset uses an explicit table list without CASCADE and rejects a live worker job. A shared PostgreSQL advisory lock protects API reads/writes against concurrent reset. Each mutating request carries the generation of the config it loaded; a stale tab must refresh.
- The model gets no DSN. API and worker roles have no ERP write privileges. The API alone can execute the guarded reset function; the worker cannot. The legacy trusted WO repository still performs its own scoped workflow DML; converting that module entirely to SECURITY DEFINER is future hardening.

## Inputs and expected outcomes

All four presets are available on `/technician/`. Machine context is the simulated AC assembly conveyor CV-01.

| Preset | Description | Qty | Origin | Expected result |
|---|---|---:|---|---|
| Stok sendiri | Bearing NTN ukuran 10x30x9 mm, karet rapat dua sisi. Kode tidak terbaca. | 1 | SYN-WH-01 | Origin available 4; no RFQs |
| Nama berbeda di gudang 2 | Bearing NTN ukuran 10x30x9 mm, karet rapat dua sisi. Kode tidak terbaca. | 6 | SYN-WH-01 | Origin insufficient; WH02 G2-BRG-017 has 8; its local name maps to the same NTN 6200LLU |
| Perbandingan vendor | Bearing NTN ukuran 10x30x9 mm, karet rapat dua sisi. Kode tidak terbaca. | 12 | SYN-WH-01 | Neither warehouse fulfills the whole quantity; compare complete vendor offers |
| Demo lengkap | Saat inspeksi sebelum shift, bearing conveyor terasa kasar saat diputar. Diameter luar 30 mm. Kode tidak terbaca. | 6 | SYN-WH-01 | Clarification: NTN; 10x30x9 mm; karet rapat dua sisi. Then WH02 alias and vendor comparison |

WH01 has physical quantity 10 and reserved quantity 6, leaving 4. WH02 has physical quantity 8 with no reservation. The reservation is an explicit synthetic assumption representing other maintenance demand. Base seed fixtures remain unchanged; deployment provisioning adds the reservation.

After identification: click **Lihat stok dan bandingkan sumber**, then **Cek stok & sumber gudang**. In the insufficient-origin cases, warehouse and vendor options are both displayed. A single source must cover the full requested quantity.

Vendor outcomes: SIM-ENOUGH (100 available), SIM-SHORT (2 available), SIM-REFUSE (rejects its one counteroffer; original quote remains), SIM-REVISE (accepts one lower price), SIM-SILENT (no response; quantity unknown). Each eligible vendor receives at most one feasible price target derived from 90% of the frozen best total expenditure across warehouses and vendors. A cheaper vendor may also be negotiated. Non-item costs are subtracted before dividing by quantity and flooring to IDR; infeasible or non-lower targets are skipped. Replaying advance never adds a second counteroffer.

Costs are illustrative, not market quotations. Normal 100 units/hour, disrupted 40, contribution IDR500,000/unit (selling price 3,500,000 less avoidable variable cost 3,000,000), recoverable output 25%, 24-hour comparison horizon. The default synthetic pre-shift calendar starts production 12 hours after WO creation; losses accrue only during the overlap of reduced capacity and scheduled production. This is an explicit demo assumption, not an assertion that downtime is free. Arrival is followed by 1 hour installation and 1 hour restart; extra recovery labor IDR250,000. Donor stock beyond reservations is assumed not to cause additional production loss. Quote tax is explicitly zero for this fixture, not a statement about tax law. In the timely quantity-six pre-shift demo, all fixture recovery finishes before production starts. Best initial total is IDR1,170,000; frozen target IDR1,053,000. SIM-REVISE accepts IDR129,666/unit, yielding comparison total IDR1,052,996 and PO invoice IDR802,996. The IDR250,000 difference is internal recovery cost, excluded from the invoice. Delayed runs and real vendor ETAs can change the result.

## Real WhatsApp demo

See [WHATSAPP_DEMO.md](WHATSAPP_DEMO.md) for private linking, quote forms, durable limits and evidence boundaries.

## Reset and recovery

Use **Reset demo**, enter `RESET DEMO`, then **Reset database demo**. Wait for identification to finish if the application says it is busy. It retains immutable PO snapshots and approval evidence while returning to an empty active manager list with the same seed stock; a second reset is supported. An old tab is rejected rather than silently submitting into the new demo generation. Reset closes active vendor conversations and cancels queued unsent messages; it preserves WhatsApp messages/audit and cannot unsend messages on recipients' phones. After a reset, replies must reference the current RFQ using WhatsApp Reply or its PP reference so old replies cannot contaminate a new run.

Complete, unambiguous bearing descriptions can use the enabled rule-first matcher, explicitly audited as deterministic with gateway_called=false. Other cases use real model calls through the existing gateway. The deployed alias is ag/gemini-3.8-flash-low; availability must be rechecked if changing gateways. The deployed worker allows 60 seconds per call, two durable attempts per job and a 90-second lease. Default library timeout remains 20 seconds outside this deployment. The earlier high-effort alias sometimes exceeded the timeout; the selected low-effort alias passed a synthetic full vendor quote extraction in about 5 seconds. This is a measured sample, not a latency guarantee. If a gateway outage persists, the WO remains failed and the UI offers the backend's bounded explicit retry; it never reports invented success. Allow up to roughly 2 minutes for a retrying identification.

## Running and maintaining this deployment

Live release directory on this VPS:
`/srv/hermes-control/services/partpilot/releases/demo-20261022`

```sh
cd /srv/hermes-control/services/partpilot/releases/demo-20261022
docker compose -f deploy/compose.yaml ps
docker compose -f deploy/compose.yaml logs --tail 30 api worker
```

Containers restart automatically. API listens only on `127.0.0.1:18080`; the dedicated PostgreSQL port is `127.0.0.1:55438`. Database volume: `partpilot-demo_demo-pg`. Do not remove the volume to perform a routine reset. Caddy config: `/srv/gateway/caddy/conf.d/partpilot.caddy`.

Runtime files are outside Git under `/home/rifqisetiawan/.config/partpilot/`, mode 0600: `demo-runtime.env` (API DB credential and demo login), `demo-worker.env` (worker DB credential), `demo-db-owner-password` (installer only), and existing `gateway-codex.env` (worker gateway only). The API container does not mount the gateway key. Neither runtime mounts the DB owner password. Do not print these files in logs or commit them.

For a new empty deployment, run `scripts/provision_demo_credentials.py` to provision scoped secrets, start the database, run `scripts/install_demo.py` with the host Python environment, then build/start API and worker. The installer refuses a different database name or an existing initialized dataset. It is not a migration script for a shared ERP.

Build after source changes with `npm ci --ignore-scripts`, `npm run build --workspace=frontend-web`, then `docker compose -f deploy/compose.yaml build api` and `docker compose -f deploy/compose.yaml up -d api worker chat-worker`. Run checks and use a new release/image tag before upgrading an in-use demo. HTTPS is configured in the existing Caddy gateway, not a second web gateway.

## Curl

Health is public; all other endpoints require the shared demo login. `-u demo` prompts for the password without embedding it in command history. Replace `GENERATION` with the numeric `generation` returned by config, and `SESSION_ID` with an actual response ID.

```sh
curl -fsS https://partpilot.rifqisetiawan.my.id/api/v1/health
curl -fsS -u demo https://partpilot.rifqisetiawan.my.id/api/v1/demo/config
curl -fsS -u demo https://partpilot.rifqisetiawan.my.id/api/v1/demo/orders

curl -fsS -u demo https://partpilot.rifqisetiawan.my.id/api/v1/work-orders \
  -H 'Content-Type: application/json' \
  -H 'X-PartPilot-Request: demo' -H 'X-PartPilot-Generation: GENERATION' \
  -H 'Idempotency-Key: manual-bearing-6-001' \
  -d '{"company_id":"SYN-COMPANY-01","site_id":"DEMO-SITE","production_line_id":"DEMO-LINE","station_id":"DEMO-STATION","machine_id":"DEMO-CONVEYOR","warehouse_id":"SYN-WH-01","description":"Bearing NTN ukuran 10x30x9 mm, karet rapat dua sisi. Kode tidak terbaca.","quantity":"6","urgency":"High"}'

curl -fsS -u demo https://partpilot.rifqisetiawan.my.id/api/v1/work-orders/SESSION_ID/submit \
  -H 'Content-Type: application/json' \
  -H 'X-PartPilot-Request: demo' -H 'X-PartPilot-Generation: GENERATION' \
  -H 'Idempotency-Key: manual-bearing-6-submit-001' -d '{"expected_version":1}'

curl -fsS -u demo https://partpilot.rifqisetiawan.my.id/api/v1/work-orders/SESSION_ID
```

Reuse the same key for retry of the same body. Use a different key for a new operation. For a complete fresh live-model API smoke (creates demo WOs), run on the VPS:

```sh
.venv/bin/python scripts/smoke_demo.py --url https://partpilot.rifqisetiawan.my.id
```

## Verification scope

Run `.venv/bin/python scripts/run_isolated_checks.py` on Linux with PostgreSQL16 binaries. This creates owned temporary clusters, never connects to the live demo or ERP, and excludes the explicitly marked live-gateway test by default. Separately exercise browser/API with the deployed worker, shared login, real gateway and synthetic fixtures. Historical acceptance suites with different retry contracts are not represented as passing by this selected suite. This deployment is an authenticated shared demo, not multi-tenant production.

Earlier simulator release verification (before the WhatsApp/description changes): 42 isolated backend regressions passed, one explicit live test deselected; real gateway flows separately passed for own stock, WH02 alias, vendor comparison (after bounded retry), and clarification. Browser reset twice, stale tab rejection, mobile layout, manager choice persistence and restart checks passed. HTTPS health200, unauthenticated401, authenticatedUI/config200. No JavaScript page errors.

## Complete-demo release, 2026-10-22

The original main frontend composition at commit `042c913` is restored: navy/blue styling, technician card, yellow clarification banner and manager tables. Warehouse/vendor sections are separate, with global exact-decimal cost ranks. Migrations 015 and 016 add immutable purchase orders and the frozen negotiation ledger. Existing decisions are not backfilled. Existing WhatsApp sessions/messages survive upgrade.

The shared planner is used by simulator and WhatsApp. Late complete vendors may join the same frozen round once. Retried or restarted work cannot create a second price proposal. Changed quote terms before dispatch are skipped rather than silently changing the approved target. Costs and competitor quotes are never included in outgoing vendor text.

For an existing deployment, back up the demo database, apply 015 then 016, grant API SELECT on the PO/negotiation tables, grant chat-worker SELECT on the negotiation tables, and grant both roles EXECUTE on `pp.demo_plan_negotiation(text)`. The chat-worker also needs EXECUTE on `pp.demo_compare(text,bigint,text,jsonb,jsonb)`. Do not grant chat-worker approval rights. Fresh bootstrap includes migrations through 016; private WhatsApp provisioning remains a separate operator step.

Verified current release: 145 isolated backend tests passed (1 live test deselected), frontend lint/build and exact-money ranking tests passed. Two real deployed browser flows used gateway clarification and simulator vendor responses: vendor selection produced a stable PO PDF for IDR802,996; warehouse selection returned no PO and showed the popup. The actual one-page PDF was rendered and visually checked. No browser errors, additional WhatsApp conversations or live resets were produced by those tests. Existing WhatsApp remained connected. The revised full live vendor negotiation loop awaits participant testing.
