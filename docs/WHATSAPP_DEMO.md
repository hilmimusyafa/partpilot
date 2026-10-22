# WhatsApp demo

The demo sends real WhatsApp messages only to explicitly configured, consenting participants. Inventory, machine economics and the shipping destination are synthetic. It never places orders or executes transfers. Vendor text is untrusted data, never instructions to tools.

## Runtime and setup

API and chat-worker use validating PostgreSQL functions for WhatsApp mutations. A separate Node/Baileys bridge binds only to authenticated loopback port 18081. API renders the private QR on `/whatsapp/`; phone session credentials stay in the private named volume. The bridge requires an explicit recipient allowlist, and the database independently requires opt-in and an active window. Recipient numbers and credentials must never enter Git. The demo window mechanism is not an assertion of official WhatsApp Cloud API template compliance.

Private files: `whatsapp.env` (bridge bearer token and allowlist), `demo-chat-worker.env` (scoped DB role), `gateway-codex.env` (model gateway). API does not receive the model key. Scope is a shared demo, not multi-tenant production.

## Operator flow

1. Link an account on the authenticated WhatsApp page. Keep participant opt-in, destination and active invitation window configured on the server.
2. Create a WO from a physical description, e.g. NTN bearing 10x30x9 mm with contact rubber seals on both sides, quantity 12, origin WH01.
3. Check stock; choose real WhatsApp rather than the simulator for this run. A single source must fulfill the quantity.
4. The initial RFQ includes the item, quantity, dummy destination, explicit demo disclaimer and a copyable blank form. Ask participants to use WhatsApp Reply.
5. Missing or ambiguous information triggers a form containing only missing fields. Unknown is not zero. Nominal total shipping and tax are required; tax percentages alone remain unknown.
6. Once complete, each eligible vendor can receive one price counteroffer. Pending negotiation remains ineligible for final selection until a usable answer/refusal arrives. The manager chooses; no procurement is executed.

## Quote form

Merek dan nomor kode :
Stok tersedia (pcs) :
Harga per pcs (Rp) :
Ongkos kirim total (Rp) :
Pajak total (Rp) :
Waktu persiapan sebelum dikirim (jam) :
Perkiraan tiba (tanggal dan jam WIB) :
Penawaran berlaku sampai (tanggal dan jam WIB) :

Use full brand and model. Arrival is distinct from preparation/dispatch. A vendor may reply 'stok kosong' or 'belum tahu' rather than invent a number. Prices, arrival and expiry must come from vendor statements.

## Durable limits and reset

Database constraints allow one counteroffer per vendor/run, at most three follow-up messages, and two extraction attempts per inbound message. Retries/restarts do not reset these budgets. Delivery uncertainty never triggers an automatic duplicate send. The bridge and DB maintain separate idempotency records. No response remains distinct from no stock.

Reset closes active conversations, cancels queued sends and preserves the external-message ledger and audit. It cannot retract messages already delivered. After reset, an unreferenced late reply stays unmatched rather than attaching to a new RFQ. Do not reset a live test while awaiting participant replies unless intentionally cancelling it.

## Verification boundaries

Owned PostgreSQL tests exercise budgets, consent/window checks, reset history, old-reply correlation, stale quotes and concurrent counteroffer requests. Bridge tests exercise replay/crash behavior without contacting vendors. Synthetic gateway extraction verifies parsing but does not demonstrate real inbound delivery. A sent transport event demonstrates outgoing delivery only; real replies, follow-up and negotiation need consenting participants to answer. Do not claim those were verified from a synthetic extractor probe.

Verification on 2026-10-22: the integrated backend suite passed 124 tests (one live-gateway test excluded). After fixing value-only excerpts from form headings, the affected WhatsApp suites passed 26 tests. A synthetic filled form sent to the real gateway produced all eight required fields in 4.04 seconds; no WhatsApp message was sent by that probe. Browser checks passed complete-description identification, clarification with physical measurements, original blue styling, mobile width and no JavaScript errors. Two authorized outgoing RFQs were transport-confirmed; live inbound/follow-up remained awaiting participant replies at verification time.
