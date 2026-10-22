# Bearing MVP acceptance — authoring only
release_ready=false. No product PASS or authorization to connect/reset DB.

## Source provenance
INSPECTED_BY_SENTINEL: original user message 110435, jarvis session 20261021_145751_9025d30c through session_search, plus follow-up messages 110437/110439. Current task confirms the five original names. Private DB-FINALIZATION-BEARING-MVP.md is a secondary design. Its table rows 41–44 omit spaces (NTN6801ZZ/NTN6900LLB/NTN6000LLH/NTN6701LLF); parent card also transcribes them incorrectly. Keep originals below; historical sources untouched.

| Verbatim name | d x D x B mm | Suffix meaning |
|---|---|---|
| NTN 6200LLU | 10x30x9 | contact both sides |
| NTN 6801ZZ | 12x21x5 | metal shields both sides |
| NTN 6900LLB | 10x22x6 | noncontact both sides |
| NTN 6000LLH | 10x26x8 | low torque both sides |
| NTN 6701LLF | 12x18x4 | noncontact; not equivalent to LLB |

Dimensions/meanings are USER-PROVIDED; MANUFACTURER-UNVERIFIED, not manufacturer verification. Description starts with that label and includes compact dimensions and suffix. D/B must not be inferred from code. No compatibility claims. IDs/stock synthetic: SYN-COMPANY-01, SYN-WH-01..05, opaque SYN-WH01-NTN-<model>, Nos, actual=10 reserved=0. WH02–05 empty and naming unknown. No invented aliases, racks/vendors/approval facts.

## Criteria and proof boundaries
| Criterion | Executable minimum | Mandatory evidence still missing |
|---|---|---|
| B01 | seed shape, five leaf warehouses, five items/bins in WH01 | authorized isolated harness preload |
| B02 | raw names, dimensions labels, existing item columns | schema-wide no parser/rules additions + public-safe docs inspection |
| B03 | all five exact hits, four empty warehouse scopes | actual 009 function execution |
| B04 | wrong category/company/warehouse decoys; disabled/group filters | SQL scope is not principal/org isolation |
| B05 | null/blank/unknown SQL returns zero | backend clarification + missing/mismatched Obsidian notes NOT VERIFIED |
| B06 | typo/case/spaces/partial/suffix/injection literal | backend driver binding/call-path inspection |
| B07 | both duplicate codes returned, no automatic merge | backend ambiguity classification NOT VERIFIED |
| B08 | zero available is hit, unlike miss | no purchase/real-stock promise |
| B09 | function metadata, indexes, tiny/large EXPLAIN | complete SQL/call-path audit, no legacy matching or fallback |
| B10 | failclosed runtime runner, baseline hashes | harness wrong-target rejection BEFORE write, SQL error abort, deterministic replay, legacy profile unchanged runtime |
| B11 | unrelated baseline tables empty, invoker function | legacy effective privileges/security/approval/org gates remain required |

SQL proposal: pp.lookup_bearing_exact(text,text,text,text), SQL/STABLE/SECURITY INVOKER, no defaults/overloads. Output ordered fields item_code,item_name,description,warehouse,actual_qty,reserved_qty,available_qty. Exact company/category/warehouse/name, Bearing only, reject disabled/group. Multiple records means ambiguity (do not select first), zero means miss in SAME scope, zero available remains a hit. No normalization, partial/fuzzy/global fallback, suffix merging, new brand/bore/suffix columns or parser/rules tables. Existing brand column is preserved, not removed. Optional exact-code path excluded from this minimum; if implemented, formally extend checks.

## Execution and isolation
Only run run_checks.py; it isolates pytest config/confcutdir and disables plugin autoload. Never run legacy conftest/reset. No DSN is read by this package. Runtime is deliberately NOT ACTIVATED. A separate officially pinned native-authorized harness must provide bearing_authorized_harness plugin, verify endpoint/current_database/principal and exclusive disposable target BEFORE any write, preload 001+009+seed with fail-fast SQL, and yield tuple-row rollback-only connections. No automatic reset/create/drop/grants. Environment flags alone are not authorization. The runtime CLI currently fails closed; its activation requires official protected revision and fresh Sentinel. Collection/static-red are the only authorized executions now.

B09 uses 5-row fixture plus 10,000 synthetic other-category records in WH01 under rollback. Capture actual EXPLAIN ANALYZE/BUFFERS JSON; small sequential scans are legitimate, no made-up latency threshold. No fixture query substitutes for the product function. B10 safety/replay and B05/B07 backend/notes evidence must be added formally, not claimed from these SQL tests. Slice acceptance cannot release the blocked legacy gate.
