# Description-first bearing and real WhatsApp demo

> Execute bounded tasks with independent verification. User authorized implementation, deployment, QR linking and demo contact; both recipients consented in chat. No real purchase authorized.

**Goal:** Technicians describe bearings, original blue UI is preserved, two private configured demo vendors can receive WhatsApp inquiries and bounded follow-ups.

**Architecture:** PostgreSQL remains authoritative. Existing synthetic procurement remains available; real WhatsApp conversations use additive durable tables and validating SECURITY DEFINER functions. A separate Node/Baileys bridge owns private device credentials and transport deduplication. Only bounded extraction sees vendor text; deterministic templates compose outgoing messages.

**Constraints:** No phones/session keys in Git. Explicit demo destination Cikarang Utara, Kabupaten Bekasi; ask vendors for estimates rather than fabricating answers. One price counteroffer per vendor/run, max three missing-field follow-ups; no unattended resend after ambiguous transport delivery. Reset cancels active chats but retains external message evidence. Manager decision does not execute procurement. Single active conversation per recipient avoids ambiguous reply routing. Initial user-authorized demo invitation uses a short explicit demo consent window, separate from the real inbound 24h reply window; no claim of official Cloud API template compliance.

## Tasks and evidence
- [ ] Descriptor matching: evidence-backed physical metadata, observable clarification, ambiguous/noncontact/brand/unsupported-modifier tests; preserve original safety tests.
- [ ] Original frontend: compare commit 042c913, restore original blue shell/landing, retain integrated API and add private QR/transcript page; lint/build and browser checks.
- [ ] Baileys bridge: pinned dependencies, private session store, allowlisted recipients, QR, durable send uncertainty/inbox dedup; fake socket restart tests.
- [ ] DB/Python chat workflow: consent/window/unique counteroffer enforcement, inbound dedup, model evidence validation, missing-field templates, real quote publication into existing comparison; owned PG tests including reset/races.
- [ ] Deploy additive schema and scoped roles, build containers, verify private endpoints and real QR connection. Never claim successful send/receive without transport evidence.
- [ ] Independent review, full relevant tests, update demo guide with natural-language inputs and actual limitations.

## Review focus
Unknown monetary values must remain unknown; tax percentage is not a nominal tax total. Vendor instructions cannot call tools or reveal internal costs. Multiple messages/restarts cannot allocate another counteroffer. Reset cannot remove already sent messages or make in-flight sends retryable. A dimension-only match cannot invent brand or interchangeable manufacturer suffixes.
