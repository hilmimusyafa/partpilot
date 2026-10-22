# Technician clarification and automatic WhatsApp demo

The user requested clarification remain with the technician, real WhatsApp become the automatic procurement transport, removal of the transport selector/WhatsApp navigation, and working stock-empty/quote/negotiation replies.

## Evidence and change
Live read-only inspection found ordinary vendor messages durably received but unmatched: historical RFQ presence required a quoted Reply even when only one current RFQ existed. Migration019 routes ordinary chat after confirmed RFQ delivery to that single active conversation. Explicit old quoted references, different PP references and older timestamps remain unmatched. Routing metadata is retained going forward, and received messages invalidate prior comparison revisions before extraction.

Historic unmatched messages cannot be safely reattached because their old records did not preserve quoted references. They are shown separately for the current vendor/timewindow and require a new reply to the active RFQ. No historic message is made an eligible quote by this migration.

Canonical forms and explicit no-stock/refusal replies parse without LLM dependence. Missing or invalid fields remain unknown. Explicitly replaced invalid/blank fields remove earlier values; they cannot borrow an old identity or price. Complete valid quotes use the existing one-round database-enforced best-total-minus-ten-percent negotiation. Empty stock is not negotiated. Initial RFQ batch creation is atomic, while persisted partial starts from older code have explicit recovery.

WO success continues on technician clarification. Only an identified WO opens manager sourcing. Opening that identified manager page starts stock checks and, when needed, WhatsApp; polling/reload does not duplicate RFQs. WhatsApp admin route is retained but hidden from primary navigation. Existing simulator history and API tests remain readable; simulator is no longer offered as a demo choice.

## Verification and preservation
Reproduced unmatched plain reply before fixing. Owned PostgreSQL routing suite covers old-reference rejection, deduplication/revisions, no-stock processing, complete form through one negotiation to revised/refused quote, atomic rollback/retry, and invalid identity revocation. Frontend tests intercept all API requests; no participant outreach. Independent reviewer verifies both layers. Existing production history, generation, stock, POs and WhatsApp session must survive deployment. No live reset or new test RFQ is authorized by the verification step itself.

## Completed acceptance
194 backend tests passed; one explicit actual-gateway test excluded, one upstream deprecation warning. Independent QA reproduced37 targeted backend tests and allfour frontend browsergroups. Both reported blockers fixed: atomic multi-recipient startup plus persistedpartialrepair, and revocation of explicitly invalid replacementfields. Build/lint passed. Migration019 applied after privatebackup with unchanged history/messages/POcounts/generation and scopedfunctionprivileges. Bridge/session unchanged.

Live acceptance: new WO success modal continued to technician clarification, real identification completed without entering manager or sending RFQ. Existing active manager page showed removed navigation/selector and unmatched-message notice; no new conversations/RFQs or browser errors. Health200 and bridgeconnected after rollout. New participantreply loop was not performed.
