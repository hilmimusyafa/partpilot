# Maintenance evidence and assessment

Mount `backend.maintenance.router.router` before the frontend static mount. The existing demo authentication, origin and generation middleware still applies. The package does not create work orders, reserve stock, approve alternatives, send messages or contact vendors.

## API

- `GET /api/v1/maintenance/evidence?kind=published_case|catalog_part|troubleshooting|economic_case`: `{items, scope}`. Each item has `id`, `kind`, `title`, `facts`, `source_refs`, `content_sha256`, `default_retrieval`, `is_local_asset_history:false`. Each source reference includes `source_id`, `url`, `locator`, source capture `sha256`, and `retrieved_at`.
- `GET /api/v1/maintenance/evidence/{evidence_id}`: one record. This route accepts `/` in catalog IDs.
- `POST /api/v1/maintenance/assess`: `{symptoms, observed_part_code?, quantity?, company_id?, warehouse_id?, machine_id?, site_id?, production_line_id?, station_id?}`. Quantity is a positive decimal string or null. Returns HTTP 201 and the persisted assessment.
- `GET /api/v1/maintenance/assessments/{id}`: retrieve the persisted assessment and tool trace.

Assessment envelope: `{id,status,request,result,model_metadata,created_at,completed_at,tool_trace}`. Terminal statuses are `completed`, `needs_review`, `failed`; **completed means the assessment finished, never that fit or a purchase was approved**. Failed or unsupported model outputs have `result.draft_work_order:null` and a bounded reason code. The call makes at most four native model turns, eight read-only tool calls, and 20 seconds per model call, with an 85-second application budget. There are no automatic model retries or fabricated fallback diagnoses.

On completion, `result` contains:

- `diagnosis:{status:'provisional_requires_inspection',summary,hypotheses:[{cause,verification,evidence_ids}]}`.
- `recommendations:[{action,evidence_ids}]`, `missing_prerequisites`, `follow_up`, and `limitations`.
- `exact_part_proposal:{sku:'PSF20CR',identity,role:'proposed_demo_exact',fit_confirmed:false,historical_case_bom:false,evidence_ids}` or null.
- `engineering_candidate:{sku:'PSF20/LP99',identity,approval_status:'PENDING_ENGINEERING_AND_HYGIENE_REVIEW',procurement_eligible:false,fit_confirmed:false,food_grade_evidence,operating_limits,evidence_ids}` or null.
- `draft_work_order:{description,quantity,context,symptoms,identity,requires_technician_confirmation:true,fit_confirmed:false,evidence_refs,note}` or null. Context is unverified user input; the existing work-order service must validate hierarchy and quantity when a technician explicitly confirms creation.
- `evidence_refs:[{evidence_id,title,source_id,url,locator,sha256,retrieved_at}]`.

Canonical identities use brand/manufacturer `RHP`, base `PSF20`, suffix `CR` or `/LP99`, full designation, and unit scope `complete_housed_unit`. Insert-only `F-UC204/LP99` is not an exact assembly. The assessment never changes identity to satisfy available stock.

## Evidence and economics

Bundled JSON extracts are copied from `outputs/PartPilot-Kasus-Nyata` and `outputs/PartPilot-Downtime-Data-Asli`. They preserve unknown historical dates, original SKUs, currency ISO codes and price years as null. They are external published OEM evidence, not local maintenance logs. Synthetic stock/vendor fixtures are deliberately not ingested.

`history:NSK-SS-E-2003` is the technical precedent. `economics:NSK-SS-E-2003` is its separate annual-cost record. `economics:NSK-SS-E-2054` is the selected separate external benchmark: `facts.reported.production_loss_rate_per_hour` is string `3332`; `facts.currency_symbol_as_published` is `$`; `facts.currency_iso_explicitly_stated` is null. Its 8.6 hours are annual, not repair hours. Secondary economic cases remain inspectable but `default_retrieval:false`. Do not combine source cases as one factory history, substitute IDR, invent throughput/margin, or add maintenance wages for every delay hour.

The loader hashes each normalized record independently of the retained raw-source capture hash. It validates HTTPS provenance and hash syntax, not the content of raw HTML/PDF snapshots (which are deliberately outside this runtime pack). Exact re-ingestion is idempotent. Changing an existing ID's facts or provenance fails; a reviewed correction requires a new evidence version.

## Installation and testing

Apply `backend/db/020_maintenance_evidence.sql` with the owner. Validate data without DB access:

```sh
python scripts/seed_maintenance_evidence.py --validate-only
```

For ingestion, set `MAINTENANCE_SEED_DATABASE_URL` explicitly to the intended owner connection and run the same script without `--validate-only`. Optional `--history-dir` and `--economics-dir` accept the original output packs. No migration, reset or external fetch happens in the script.

Runtime grants: schema usage; SELECT on `pp.maintenance_evidence`; SELECT/INSERT/UPDATE on `pp.maintenance_assessment`; SELECT/INSERT on `pp.maintenance_tool_trace`. Runtime must have no evidence INSERT/UPDATE/DELETE grants. Evidence and traces have update/delete rejection triggers; completed assessments reject updates. Each successful or rejected tool call stores arguments, source-backed result, evidence IDs, sequence and timing. Opaque provider reasoning/signatures stay in memory only; the stored/public trace excludes them. Model tools cannot access SQL, arbitrary files or network URLs.

Portable tests: `pytest tests/codex/test_maintenance_agent.py`. Owned PostgreSQL16 integration: `pytest tests/codex/test_maintenance_db.py`; it uses the existing private-cluster harness and never a production DSN. The gateway adapter is injected only at the external boundary in deterministic tests; the production agent uses `backend.wo.gateway.call_agent_turn` and chooses its own tools.
