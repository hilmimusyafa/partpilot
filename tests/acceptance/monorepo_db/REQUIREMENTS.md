# Monorepo DB publication acceptance (authoring only)

Scope: new backend SQL/documentation bundle. Frontend is deferred. Original files
remain at their original paths, byte-identical; do not move/delete/repair historical
acceptance. This is not full application/security approval.

M01: backend/db/001_schema.sql and backend/db/009_bearing_lookup.sql are byte copies
of frozen originals. New backend/db/seed/009_bearing_mvp_synth.sql contains the
combined synthetic snapshot. Required docs: backend/README.md and
backend/docs/db/bearing-mvp.md.
M02: configured public-marker scan over these five paths only, plus human exact
publication diff review by Relay. No real catalog/credentials/private absolute
paths or agent/model markers. A finite scan does not establish authorship or
exhaustive secret detection. Root README is optional and only publishable if
explicitly authorized; Relay reviews it if included. No frontend implementation.
M03: portable documented psql commands with -f, order 001 -> 009 -> combined seed.
backend/README.md commands run from backend/; backend/docs/db/bearing-mvp.md
commands run from repository root. Use locally configured connection, never a
credential literal. This exact small command convention is chosen for reproducibility.
M04: exact eight joined readbacks and exact scoped lookup results, according to
expected.json: five WH01 original records stock 10; three user WH02 records
stock 8/14/9. All reserved 0, Bearing, Nos (individual pieces), NTN. Preserve
WH01 descriptions and WH02 recorded descriptions exactly, including simulation,
label/location and local-code-not-MPN provenance. No inferred matching logic.
M05: 1 company, 5 leaf warehouses, 1 category, 8 items/8 bins. WH03..05 empty;
replaying seed twice leaves full row snapshots identical (not just counts).
M06: mismatching company currency, warehouse state, category, item name/description,
stock or reserved values must raise a PostgreSQL error; never overwrite or silently
ignore mismatch. Each adverse case is isolated by savepoint. These representative
cases do not claim enumeration of every conflict field; human review confirms
complete guards for all seed-owned fields.
M07: company/category/warehouse boundaries and literal exact-name semantics;
WH02 local names do not become label aliases. No fuzzy lookup.
M08: original lookup function and indexes preserved; seed cannot add columns.

Execution: dedicated existing partpilot_bearing_test only, owner/principal
pp_migrator, loopback:5432; never main. Reuse approved local credential resolver
without printing DSN; shared session advisory lock 58057083, empty-target
preflight before writes, SQL boundaries, timeouts, one uncommitted transaction,
per-case savepoints, rollback and post-run empty-object check. No grants/admin/
reset or new database. Runtime is an executable future gate, not an unconditional
activation guard. Only collection/static-red authorized during this authoring run.

Source provenance: original WH01 seed is INSPECTED_BY_SENTINEL. WH02 requirements
are from t_56b741a2 body and its recorded run96 evidence (not a fresh database dump).
Live commit/readback is UPSTREAM_REPORTED, not independently rerun here.
