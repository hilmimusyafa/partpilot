# Five-warehouse and live manager demo follow-up

User-authorized enhancement to the existing deployed demo; preserve original styling, vendor consent/budgets, manager-only choice, immutable PO history and current data. No live reset or test outreach to participants. Synthetic addresses and inventory are explicitly labeled.

## Acceptance
- Stock cards explain canonical identity, local names, physical/reserved/available quantities, required quantity and shortage. All five warehouses have names and dummy addresses.
- Add exact NTN 6200LLU records in WH03/04/05, available 2/3/1, using scoped local naming knowledge and explicit database identity evidence. All are insufficient for main demo quantity6. Reset restores these fixtures. Existing snapshots remain historical, not rewritten.
- Trace WhatsApp inbound -> extraction -> run revision -> comparison -> UI. Refresh complete and partial vendor changes automatically without polling mutations forever; interrupted polls recover; expired/stale options cannot be approved. Current live conversations are closed after reset, so do not resurrect or resend them.
- Manager vendor selection creates one persistent PO using existing approval transaction; warehouse choice records a demo request and shows success, without claiming staff notification or physical movement.
- WO creation shows a truthful success modal with continue-clarification and manager navigation. Submit failure is not a successful submission. Manager can follow processing/clarification/identified state without refresh.
- Preserve blue/navy original design and compare warehouses/vendors separately.

## Work and evidence
- Frontend owner: cards, polling, request popup, WO success modal, intercepted evolving-response browser tests, lint/build.
- Data owner: additive migration017, scoped knowledge and reset fixtures, API warehouse metadata, owned database tests.
- Root: direct manager order read, extraction revision invalidation migration018, isolated regression reproduction, deployment and real browser simulator flow.
- Independent reviewer reproduces selected acceptance evidence. Test data stay synthetic, participant replies remain deferred.

## Observed causes
- Decision page polls sourcing run and conversations but does not refresh comparison.
- The list endpoint is capped at100 while detail previously depended on that list.
- Partial/review extraction and parser exhaustion did not increment sourcing revision, so version-based comparison refresh would miss eligibility changes.
- Four current WhatsApp conversations are closed and absent from active work orders; resets intentionally preserve history without accepting replies into fresh WOs.

## Completed evidence
- Reproduced four initial regressions: missing direct detail endpoint and unchanged sourcing version for partial/review/exhausted parsing. All five final dashboard regressions pass, including older-than100 detail, foreign-company404, blocked stale approval/no PO, and closed-conversation preservation.
- Migration017:7 owned tests pass, covering all five scoped identities, same natural description across distinct codes, exact2/3/1 stock, reset, replay with modified live stock, preserved workflows/messages/POs and refusal of foreign company.
- Full backend suite:157 passed,1 explicit live-gateway test deselected,1 non-failing upstream deprecation warning.
- Frontend lint/build and precise ranking tests pass. Independent reviewer reproduced all three browser groups including evolving WA responses, refresh409/retry, chat-read failure, pending-again, approval races, other-tab selection, failed submission recovery and WO navigation. No blockers.
- Added migrations after private backup. API read permissions verified; generations and counts of existing WOs/messages/POs preserved. No reset or participant outreach performed.
- Deployed real browser: two new synthetic flows passed WO success modal, manager navigation, real-gateway clarification, all five warehouse cards, simulator comparison, vendor approval/PDF persistence and warehouse request popup/no PO. Zero browser errors and no new WhatsApp conversations.
- Generated PDF visually inspected: six NTN6200LLU, unit129666, invoice802996; internal250000 recovery remains outside invoice. Warehouse cards and WO modal visually inspected.
- Real participant-dependent WA negotiation remains deferred. This verification does not assert end-to-end delivery of a new participant reply.
