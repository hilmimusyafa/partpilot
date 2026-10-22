"""Owned PostgreSQL16 food flow: public evidence, exact sourcing, explicit upgrade gates."""
import json
import sys
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb

sys.path.insert(0, str(Path(__file__).parent))
from isolated import Cluster
from test_maintenance_agent import CALLS, complete_sequence, final_reply, records, tool_reply

ROOT = Path(__file__).resolve().parents[2]
FOOD_CONTEXT = dict(company_id='SYN-COMPANY-01', site_id='FOOD-SITE', production_line_id='FOOD-LINE',
                    station_id='FOOD-STATION', machine_id='FOOD-CONVEYOR', warehouse_id='SYN-WH-01')
ACK = dict(external_applicability_acknowledged=True, idr_per_published_currency_unit='18000',
           conversion_assumption_acknowledged=True)
CHECKS = dict(interface_load_speed_checked=True, temperature_duty_checked=True, hygiene_approved=True)


@pytest.fixture
def food(request, monkeypatch):
    from backend.demo.bootstrap import install_demo
    from backend.maintenance.repository import PostgresStore, seed_records
    from backend.maintenance.agent import assess
    from backend.maintenance.models import AssessmentInput
    c = Cluster()
    monkeypatch.setenv('DATABASE_URL', c.dsn)
    monkeypatch.setenv('TEST_DATABASE_URL', c.dsn)
    monkeypatch.setenv('PARTPILOT_DEMO_PASSWORD', 'food-tests-only')
    monkeypatch.delenv('PARTPILOT_DEMO_PUBLIC_ACCESS', raising=False)
    try:
        with c.connection() as conn:
            conn.execute("DELETE FROM erp.company WHERE name LIKE 'foreign-%'")
            install_demo(conn, allow_test_database=True)
            for filename, marker in [('020_maintenance_evidence.sql', 'pp.maintenance_evidence'),
                                     ('021_complete_part_identity.sql', 'pp.valid_part_identity(jsonb)'),
                                     ('022_food_demo.sql', 'pp.maintenance_work_order')]:
                function = 'to_regprocedure' if '(' in marker else 'to_regclass'
                if not conn.execute(f'SELECT {function}(%s) found', (marker,)).fetchone()['found']:
                    conn.execute((ROOT / 'backend/db' / filename).read_text(), prepare=False)
            evidence = records()
            if getattr(request, 'param', None) == 'without_benchmark':
                evidence = [r for r in evidence if r['id'] != 'economics:NSK-SS-E-2054']
            if getattr(request, 'param', None) == 'without_original_catalog':
                evidence = [r for r in evidence if r['id'] != 'catalog:PSF20CR']
            seed_records(conn, evidence)
        result = None
        if getattr(request, 'param', None) != 'without_original_catalog':
            result = assess(AssessmentInput(**FOOD_CONTEXT, symptoms='Conveyor bearing corrosion after washdown', quantity='2'),
                            store=PostgresStore(c.connection), complete=complete_sequence(tool_reply(CALLS), final_reply()))
            assert result['status'] == 'completed'
        from backend.demo.app import app
        with TestClient(app) as client:
            client.auth = ('demo', 'food-tests-only')
            client.headers.update({'X-PartPilot-Request': 'demo', 'X-PartPilot-Generation': '1'})
            yield c, client, result
    finally:
        c.close()


def confirm(client, aid, kind='exact', **changes):
    body = dict(part_kind=kind, observed_part_code='RHP PSF20CR' if kind == 'exact' else 'RHP PSF20/LP99',
                quantity='2', technician='Technician test', inspected_and_confirmed=True)
    body.update(changes)
    return client.post(f'/api/v1/food-demo/assessments/{aid}/work-orders', json=body,
                       headers={'Idempotency-Key': uuid.uuid4().hex})


def review(client, aid, **changes):
    body = dict(reviewer='Engineer test', decision='approved', notes='Inspected interface, duty and hygiene suitability.', **CHECKS)
    body.update(changes)
    return client.post(f'/api/v1/food-demo/assessments/{aid}/engineering-review', json=body)


def start_identified(c, client, aid, kind='exact'):
    response = confirm(client, aid, kind)
    assert response.status_code == 201, response.text
    wo = response.json()
    code = 'DEMO-RHP-PSF20CR' if kind == 'exact' else 'DEMO-RHP-PSF20-LP99'
    candidate = c.sql('SELECT item_code,item_name,brand,description FROM erp.item WHERE item_code=%s', (code,))[0]
    # State-machine tests supply a confirmed identity; the full worker path is
    # exercised separately below, without allowing a network model call.
    c.sql("UPDATE pp.wo_identification_session SET state='identified',version=version+1,result=%s WHERE id=%s",
          (Jsonb({'identified_candidate': candidate}), wo['id']))
    version = c.sql('SELECT version FROM pp.wo_identification_session WHERE id=%s', (wo['id'],))[0]['version']
    run = client.post('/api/v1/demo/sourcing-runs', json={'session_id': wo['id'], 'expected_version': version},
                      headers={'Idempotency-Key': uuid.uuid4().hex})
    assert run.status_code == 201, run.text
    return run.json()


def comparison(client, run):
    result = client.post(f"/api/v1/food-demo/sourcing-runs/{run['id']}/comparison", json=ACK,
                         headers={'Idempotency-Key': uuid.uuid4().hex})
    assert result.status_code == 201, result.text
    return result.json()


def test_food_context_and_external_evidence_are_readable_and_durable(food):
    c, client, result = food
    config = client.get('/api/v1/food-demo/config')
    assert config.status_code == 200 and config.json()['context'] == FOOD_CONTEXT
    response = client.get('/api/v1/production-lines', params={'company_id': 'SYN-COMPANY-01', 'site_id': 'FOOD-SITE'})
    assert response.status_code == 200, response.text
    assert any(row['id'] == 'FOOD-LINE' and row['production_scope'] == 'FOOD' for row in response.json()['items'])
    evidence = client.get('/api/v1/maintenance/evidence/history:NSK-SS-E-2003')
    assert evidence.status_code == 200 and evidence.json()['is_local_asset_history'] is False
    assert evidence.json()['facts']['historical_original_sku'] is None
    assert len(evidence.json()['source_refs'][0]['sha256']) == 64
    recovered = client.get('/api/v1/maintenance/assessments/' + result['id']).json()
    assert recovered['result']['evidence_refs'] == result['result']['evidence_refs']
    assert len(recovered['tool_trace']) == 4
    with pytest.raises(psycopg.Error, match='immutable'):
        c.sql("UPDATE pp.maintenance_evidence SET facts='{}' WHERE id='history:NSK-SS-E-2003'")


def test_confirmed_exact_work_order_queues_and_identifies_original_without_alternative_leak(food, monkeypatch):
    from backend.wo import worker
    c, client, result = food
    response = confirm(client, result['id'])
    assert response.status_code == 201, response.text
    wo = response.json()
    assert wo['state'] == 'queued' and wo['machine_id'] == 'FOOD-CONVEYOR'
    # Reproduce the grounded phrase returned by the live extractor: a category
    # span can name the complete flange unit instead of only saying "bearing".
    extraction = {'facts': [{'key': 'category', 'value': 'Bearing', 'source': 'description',
        'evidence': [{'source_field': 'description', 'raw_substring': 'bearing unit flange',
                      'normalized_value': 'Bearing'}]}]}
    prompts = []
    def extracted(messages, **kwargs):
        prompts.extend(messages)
        return dict(status='ok', content=json.dumps(extraction), model='test-extraction')
    monkeypatch.setattr(worker.gateway, 'call_gateway_completion', extracted)
    job = worker.claim_next_job('food-tests')
    assert job and job['session_id'] == wo['id']
    worker.process_job(job)
    recovered = client.get('/api/v1/work-orders/' + wo['id']).json()
    assert recovered['state'] == 'identified', recovered
    assert recovered['result']['identified_item_code'] == 'DEMO-RHP-PSF20CR'
    source = c.sql("SELECT source_refs,content_sha256 FROM pp.maintenance_evidence WHERE id='catalog:PSF20CR'")[0]
    ref = recovered['knowledge_refs'][0]
    assert ref['path'] == source['source_refs'][0]['url']
    assert ref['sha256'] == source['source_refs'][0]['sha256']
    assert ref['source_status'].startswith('OEM_CATALOG_EXTRACT')
    assert ref['snapshot_version'] == source['content_sha256']
    assert source['source_refs'][0]['url'] in prompts[1]['content']
    assert 'MANUFACTURER-UNVERIFIED' not in prompts[1]['content']
    assert 'NTN' not in prompts[1]['content']
    replay = confirm(client, result['id'])
    assert replay.status_code == 201 and replay.json()['id'] == wo['id']
    assert c.sql('SELECT count(*) n FROM pp.maintenance_work_order')[0]['n'] == 1


@pytest.mark.parametrize('food', ['without_original_catalog'], indirect=True)
def test_food_worker_fails_closed_without_catalog_evidence(food, monkeypatch):
    from backend.wo import worker
    c, client, _ = food
    response = client.post('/api/v1/work-orders', json=dict(**FOOD_CONTEXT,
        description='Ganti bearing unit flange lengkap RHP PSF20CR', quantity='2', urgency='High'),
        headers={'Idempotency-Key': uuid.uuid4().hex})
    assert response.status_code == 201, response.text
    wo = response.json()
    response = client.post(f"/api/v1/work-orders/{wo['id']}/submit", json={'expected_version': wo['version']},
                           headers={'Idempotency-Key': uuid.uuid4().hex})
    assert response.status_code in (200, 202), response.text
    def unavailable_model(*args, **kwargs):
        pytest.fail('Missing OEM evidence must stop before model extraction')
    monkeypatch.setattr(worker.gateway, 'call_gateway_completion', unavailable_model)
    worker.process_job(worker.claim_next_job('food-missing-catalog'))
    recovered = client.get('/api/v1/work-orders/' + wo['id']).json()
    assert recovered['state'] == 'knowledge_unavailable', recovered
    assert recovered['result']['reason'] == 'food_catalog_evidence_missing'


@pytest.mark.parametrize('check', tuple(CHECKS))
def test_candidate_requires_every_engineering_check_before_work_order(food, check):
    c, client, result = food
    aid = result['id']
    assert confirm(client, aid, 'candidate').status_code == 422
    assert review(client, aid, **{check: False}).status_code == 422
    assert confirm(client, aid, 'candidate').status_code == 422
    assert not c.sql('SELECT * FROM pp.maintenance_work_order')
    approved = review(client, aid)
    assert approved.status_code == 201, approved.text
    candidate = confirm(client, aid, 'candidate')
    assert candidate.status_code == 201, candidate.text
    link = c.sql('SELECT * FROM pp.maintenance_work_order')[0]
    assert link['part_kind'] == 'candidate' and link['engineering_review_id'] == approved.json()['id']


def test_blank_reviewer_cannot_approve_candidate(food):
    c, client, result = food
    assert review(client, result['id'], reviewer='  ').status_code == 422
    assert not c.sql('SELECT * FROM pp.maintenance_engineering_review')


def test_benchmark_requires_applicability_and_currency_ack_before_ranking(food):
    c, client, result = food
    run = start_identified(c, client, result['id'])
    for missing in ('external_applicability_acknowledged', 'idr_per_published_currency_unit', 'conversion_assumption_acknowledged'):
        body = {k: v for k, v in ACK.items() if k != missing}
        response = client.post(f"/api/v1/food-demo/sourcing-runs/{run['id']}/comparison", json=body,
                               headers={'Idempotency-Key': uuid.uuid4().hex})
        assert response.status_code == 422
    assert not c.sql('SELECT * FROM pp.demo_comparison')
    ranked = comparison(client, run)
    assert ranked['production']['mode'] == 'reported_downtime_rate'
    assert ranked['production']['source_currency_iso'] is None
    assert ranked['production']['case_id'] == 'NSK-SS-E-2054'
    assert ranked['eligible_complete_options']
    option = ranked['eligible_complete_options'][0]
    assert option['quote']['identity']['full_designation'] == 'PSF20CR'
    assert option['economics']['unrecoverable_lost_contribution'] is None
    assert option['economics']['estimated_production_loss'] is not None


@pytest.mark.parametrize('food', ['without_benchmark'], indirect=True)
def test_missing_persisted_benchmark_cannot_be_replaced_with_legacy_margin(food):
    c, client, result = food
    run = start_identified(c, client, result['id'])
    response = client.post(f"/api/v1/food-demo/sourcing-runs/{run['id']}/comparison", json=ACK,
                           headers={'Idempotency-Key': uuid.uuid4().hex})
    assert response.status_code == 503, response.text
    assert response.json()['error']['code'] == 'benchmark_evidence_missing'
    assert not c.sql('SELECT * FROM pp.demo_comparison')


def test_food_run_cannot_use_legacy_demo_margin_shortcut(food):
    c, client, result = food
    run = start_identified(c, client, result['id'])
    response = client.post(f"/api/v1/demo/sourcing-runs/{run['id']}/prepare-comparison", json={},
                           headers={'Idempotency-Key': uuid.uuid4().hex})
    assert response.status_code == 422, response.text
    assert not c.sql('SELECT * FROM pp.demo_comparison')


def test_food_run_cannot_submit_legacy_margin_to_generic_comparison_endpoint(food):
    from test_procurement import comparison_input
    c, client, result = food
    run = start_identified(c, client, result['id'])
    body = comparison_input(run)
    body['options'] = [{**body['options'][0], 'source_id': 'SYN-WH-02'}]
    response = client.post(f"/api/v1/demo/sourcing-runs/{run['id']}/comparisons", json=body,
                           headers={'Idempotency-Key': uuid.uuid4().hex})
    assert response.status_code == 422, response.text
    assert not c.sql('SELECT * FROM pp.demo_comparison')


def test_food_vendor_collection_waits_for_benchmark_ack_before_negotiation(food):
    c, client, result = food
    run = start_identified(c, client, result['id'])
    response = client.post(f"/api/v1/demo/sourcing-runs/{run['id']}/advance", json={})
    assert response.status_code == 200, response.text
    assert len(c.sql("SELECT id FROM pp.demo_outbox WHERE kind='rfq'")) == 5
    assert not c.sql("SELECT id FROM pp.demo_outbox WHERE kind='price_counteroffer'")
    assert not c.sql('SELECT * FROM pp.demo_comparison')
    assert not c.sql('SELECT * FROM pp.demo_negotiation_round')
    comparison(client, response.json())
    response = client.post(f"/api/v1/demo/sourcing-runs/{run['id']}/advance", json={})
    assert response.status_code == 200, response.text
    rounds = c.sql('SELECT basis FROM pp.demo_negotiation_round')
    assert len(rounds) == 1
    assert rounds[0]['basis']['production']['mode'] == 'reported_downtime_rate'
    assert rounds[0]['basis']['production']['external_applicability_acknowledged'] is True
    assert all(row['snapshot']['production']['mode'] == 'reported_downtime_rate'
               for row in c.sql('SELECT snapshot FROM pp.demo_comparison'))


@pytest.mark.parametrize('food', ['without_benchmark'], indirect=True)
def test_generic_comparison_cannot_skip_persisted_benchmark_evidence(food):
    from test_procurement import comparison_input
    from backend.procurement.benchmark import ReportedDowntimeBenchmark
    c, client, result = food
    run = start_identified(c, client, result['id'])
    body = comparison_input(run)
    body['production'] = ReportedDowntimeBenchmark(**ACK).model_dump()
    body['options'] = [{**body['options'][0], 'source_id': 'SYN-WH-02'}]
    response = client.post(f"/api/v1/demo/sourcing-runs/{run['id']}/comparisons", json=body,
                           headers={'Idempotency-Key': uuid.uuid4().hex})
    assert response.status_code == 503, response.text
    assert response.json()['error']['code'] == 'benchmark_evidence_missing'
    assert not c.sql('SELECT * FROM pp.demo_comparison')


def test_database_blocks_selection_of_both_original_and_candidate(food):
    c, client, result = food
    aid = result['id']
    original = comparison(client, start_identified(c, client, aid))
    assert review(client, aid).status_code == 201
    candidate = comparison(client, start_identified(c, client, aid, 'candidate'))
    first = original['eligible_complete_options'][0]
    second = candidate['eligible_complete_options'][0]
    c.sql('SELECT pp.demo_choose(%s,1,%s,%s)', (original['id'], first['option_id'], uuid.uuid4().hex))
    with pytest.raises(psycopg.Error, match='maintenance_request_already_selected'):
        c.sql('SELECT pp.demo_choose(%s,1,%s,%s)', (candidate['id'], second['option_id'], uuid.uuid4().hex))
    assert c.sql('SELECT count(*) n FROM pp.demo_decision')[0]['n'] == 1


def test_later_rejection_blocks_selection_of_previously_approved_candidate(food):
    c, client, result = food
    aid = result['id']
    assert review(client, aid).status_code == 201
    ranked = comparison(client, start_identified(c, client, aid, 'candidate'))
    assert review(client, aid, decision='rejected', hygiene_approved=False).status_code == 201
    option = ranked['eligible_complete_options'][0]
    with pytest.raises(psycopg.Error):
        c.sql('SELECT pp.demo_choose(%s,1,%s,%s)', (ranked['id'], option['option_id'], uuid.uuid4().hex))
    assert not c.sql('SELECT * FROM pp.demo_decision')


def test_completed_assessment_without_part_proposal_cannot_create_fixed_catalog_work_order(food):
    from backend.maintenance.agent import assess
    from backend.maintenance.models import AssessmentInput
    from backend.maintenance.repository import PostgresStore
    c, client, _ = food
    result = assess(AssessmentInput(**FOOD_CONTEXT, symptoms='Bearing failure; marking unknown', quantity='2'),
                    store=PostgresStore(c.connection), complete=complete_sequence(
                        tool_reply(CALLS), final_reply(requested_part_sku=None, alternative_part_sku=None)))
    assert result['status'] == 'completed' and result['result']['exact_part_proposal'] is None
    for kind in ('exact', 'candidate'):
        response = confirm(client, result['id'], kind)
        assert response.status_code == 422, response.text
        assert response.json()['error']['code'] == 'part_proposal_not_supported'
    assert not c.sql('SELECT * FROM pp.maintenance_work_order')


def test_database_rejects_approved_review_without_all_checks(food):
    c, _, result = food
    with pytest.raises(psycopg.Error):
        c.sql("INSERT INTO pp.maintenance_engineering_review(assessment_id,reviewer,decision,checks,notes) VALUES(%s,'Engineer test','approved',%s,'Approval missing hygiene verification')",
              (result['id'], Jsonb({**CHECKS, 'hygiene_approved': False})))
    assert not c.sql('SELECT * FROM pp.maintenance_engineering_review')


def test_direct_unlinked_upgrade_cannot_start_sourcing(food):
    c, client, _ = food
    response = client.post('/api/v1/work-orders', json=dict(**FOOD_CONTEXT,
        description='Ganti bearing unit flange lengkap RHP PSF20/LP99', quantity='2', urgency='High'),
        headers={'Idempotency-Key': uuid.uuid4().hex})
    assert response.status_code == 201, response.text
    wo = response.json()
    candidate = c.sql("SELECT item_code,item_name,brand,description FROM erp.item WHERE item_code='DEMO-RHP-PSF20-LP99'")[0]
    c.sql("UPDATE pp.wo_identification_session SET state='identified',version=2,result=%s WHERE id=%s",
          (Jsonb({'identified_candidate': candidate}), wo['id']))
    response = client.post('/api/v1/demo/sourcing-runs', json={'session_id': wo['id'], 'expected_version': 2},
                           headers={'Idempotency-Key': uuid.uuid4().hex})
    assert response.status_code == 409, response.text
    assert response.json()['error']['code'] == 'engineering_approval_required'
    assert not c.sql('SELECT * FROM pp.demo_run')


def test_opted_out_whatsapp_participant_does_not_block_authorized_participant(food, monkeypatch):
    from backend.whatsapp import service
    c, _, _ = food
    # The owned test cluster has no live recipients; only /status is mocked,
    # so this verifies the real consent query without making any outbound call.
    c.sql("INSERT INTO pp.wa_recipient(id,phone,label,opted_in,consent_source,destination,demo_invite_until) VALUES ('WA-DEMO-1','620000000001','Authorized test participant',true,'test fixture','Synthetic destination',now()+interval '1 day'),('WA-DEMO-2','620000000002','Opted out test participant',false,NULL,'Synthetic destination',NULL)")
    assert len(c.sql('SELECT id FROM pp.wa_recipient WHERE NOT opted_in')) >= 1
    calls = []
    def connected_status(path, body=None):
        calls.append((path, body))
        return {'connection': 'connected', 'enabled': True, 'qr_data_url': None}
    monkeypatch.setattr(service, 'bridge', connected_status)
    state = service.status()
    assert state['can_start'] is True and state['blocked_reason'] is None
    assert len(state['recipients']) == 1
    assert calls == [('/status', None)]


def test_late_vendor_comparison_persists_full_recovery_cost_on_common_horizon(food):
    from backend.procurement.service import advance
    from backend.procurement.simulator import DemoSimulator
    c, client, result = food
    run = start_identified(c, client, result['id'])

    class LateVendor(DemoSimulator):
        def send(self, event):
            reply = super().send(event)
            if event['vendor_id'] == 'SIM-ENOUGH' and reply.quote:
                reply.quote.delivered_eta = datetime.fromisoformat(event['payload']['requested_at']) + timedelta(hours=96)
            return reply

    quoted = advance(run['id'], transport=LateVendor())
    ranked = comparison(client, quoted)
    late = next(o for o in ranked['eligible_complete_options'] if o['source_id'] == 'SIM-ENOUGH')
    economics = late['economics']
    restore_at = datetime.fromisoformat(late['quote']['delivered_eta']) + timedelta(hours=2)
    assert datetime.fromisoformat(economics['restore_at']) == restore_at
    assert Decimal(economics['effective_scheduled_impacted_hours']) > 97
    assert economics['effective_scheduled_impacted_hours'] == economics['elapsed_restore_hours']
    assert Decimal(economics['estimated_production_loss_unrounded']) == (
        Decimal(economics['effective_scheduled_impacted_hours']) * Decimal('3332') * Decimal('18000'))
    schedules = [o['assumptions']['schedule'] for o in ranked['eligible_complete_options']]
    assert {s['horizon_end'] for s in schedules} == {restore_at.isoformat()}
    assert all(s['calendar_source'] == 'synthetic:continuous production; full stop' for s in schedules)
    stored = c.sql('SELECT request,snapshot FROM pp.demo_comparison WHERE id=%s', (ranked['id'],))[0]
    assert {o['schedule']['horizon_end'] for o in stored['request']['options']} == {restore_at.isoformat()}
    persisted = next(o for o in stored['snapshot']['eligible_complete_options'] if o['source_id'] == 'SIM-ENOUGH')
    assert persisted['economics'] == economics
    assert not c.sql('SELECT * FROM pp.wa_conversation')


def test_generic_food_comparison_cannot_rank_a_horizon_ending_before_recovery(food):
    from backend.demo.food import recovery_options
    from backend.procurement.benchmark import ReportedDowntimeBenchmark
    from backend.procurement.comparison import sources
    c, client, result = food
    run = start_identified(c, client, result['id'])
    start = datetime.now(timezone.utc)
    source = next(s for s in sources(run) if s['source_id'] == 'SYN-WH-02')
    source['quote']['delivered_eta'] = (start + timedelta(hours=72)).isoformat()
    assumption = recovery_options([source], start)[0]
    cutoff = (start + timedelta(hours=48)).isoformat()
    assumption['schedule']['horizon_end'] = cutoff
    assumption['schedule']['scheduled_impacted_windows'][0]['end'] = cutoff
    body = dict(expected_version=run['version'], production=ReportedDowntimeBenchmark(**ACK).model_dump(), options=[assumption])
    response = client.post(f"/api/v1/demo/sourcing-runs/{run['id']}/comparisons", json=body,
                           headers={'Idempotency-Key': uuid.uuid4().hex})
    assert response.status_code == 201, response.text
    ranked = response.json()
    assert ranked['status'] == 'incomplete'
    assert not ranked['eligible_complete_options']
    partial = next(o for o in ranked['unrankable_options'] if o['source_id'] == 'SYN-WH-02')
    assert '/schedule/horizon_end_before_restore' in partial['reasons']
    assert partial['economics']['future_relevant_option_total'] is None
    assert partial['economics']['effective_scheduled_impacted_hours'] == '48'


@pytest.mark.parametrize('kind,sku', [('exact', 'PSF20CR'), ('candidate', 'PSF20/LP99')])
def test_food_availability_snapshot_uses_selected_oem_catalog_provenance(food, kind, sku):
    c, client, result = food
    if kind == 'candidate':
        assert review(client, result['id']).status_code == 201
    run = start_identified(c, client, result['id'], kind)
    catalog = c.sql('SELECT source_refs,content_sha256 FROM pp.maintenance_evidence WHERE id=%s', ('catalog:' + sku,))[0]
    availability = run['availability']
    for scope in [availability['origin'], *availability['alternatives']]:
        assert scope['knowledge_refs'], scope
        ref = scope['knowledge_refs'][0]
        assert ref['path'] == catalog['source_refs'][0]['url']
        assert ref['sha256'] == catalog['source_refs'][0]['sha256']
        assert ref['snapshot_version'] == catalog['content_sha256']
        assert ref['source_status'].startswith('OEM_CATALOG_EXTRACT')
        assert ref['warehouse_id'] == scope['warehouse_id']
        assert json.loads(ref['content_snapshot'])['facts']['part']['sku'] == sku
    stored = c.sql('SELECT snapshot FROM pp.demo_run WHERE id=%s', (run['id'],))[0]['snapshot']
    assert stored['availability'] == availability


@pytest.mark.parametrize('food', ['without_original_catalog'], indirect=True)
def test_food_availability_cannot_fall_back_when_oem_catalog_is_missing(food, monkeypatch):
    from backend.wo import availability
    from backend.wo.identity import complete_identity
    _, _, _ = food
    def forbidden_fallback(*args, **kwargs):
        pytest.fail('Complete RHP unit cannot use a legacy note or search stock without OEM evidence')
    monkeypatch.setattr(availability, 'load_scoped_note', forbidden_fallback)
    monkeypatch.setattr(availability, 'get_scoped_candidates', forbidden_fallback)
    result = availability.evaluate_scope('SYN-WH-02', Decimal('2'), complete_identity('PSF20CR'))
    assert result.status == 'knowledge_unavailable'
    assert result.scoped_reason == 'food_catalog_evidence_missing'
    assert result.knowledge_refs[0]['source_status'] == 'UNAVAILABLE'
    assert result.item_code is None and not result.evidence


@pytest.mark.parametrize('company,warehouse,category', [
    ('OTHER-COMPANY', 'SYN-WH-02', 'Bearing'),
    ('SYN-COMPANY-01', 'SYN-WH-99', 'Bearing'),
    ('SYN-COMPANY-01', 'SYN-WH-02', 'Motor'),
])
def test_food_catalog_availability_remains_company_warehouse_and_category_scoped(food, monkeypatch, company, warehouse, category):
    from backend.wo import availability
    from backend.wo.identity import complete_identity
    _, _, _ = food
    def forbidden_stock_lookup(*args, **kwargs):
        pytest.fail('Unavailable catalog scope must stop before stock lookup')
    monkeypatch.setattr(availability, 'get_scoped_candidates', forbidden_stock_lookup)
    result = availability.evaluate_scope(warehouse, Decimal('2'), complete_identity('PSF20CR'), category, company)
    assert result.status == 'knowledge_unavailable'
    assert result.scoped_reason == 'food_catalog_scope_unavailable'
