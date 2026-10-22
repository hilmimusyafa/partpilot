"""Portable evidence/agent tests: model and database are external boundaries."""
import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PACKS = ROOT / 'backend/maintenance/evidence_pack'


class EvidenceStore:
    """Test-only persistence double; the agent and validation remain real."""
    def __init__(self, records):
        self.records = {r['id']: r for r in records}
        self.assessments = {}

    def list_evidence(self, kind=None):
        return [copy.deepcopy(v) for v in self.records.values() if not kind or v['kind'] == kind]

    def get_evidence(self, evidence_id):
        return copy.deepcopy(self.records.get(evidence_id))

    def create_assessment(self, request):
        ident = 'test-assessment'
        self.assessments[ident] = dict(id=ident, request=request, status='running', result=None, tool_trace=[])
        return ident

    def append_trace(self, ident, trace):
        self.assessments[ident]['tool_trace'].append(copy.deepcopy(trace))

    def finish_assessment(self, ident, status, result, metadata):
        self.assessments[ident].update(status=status, result=result, model_metadata=metadata)

    def get_assessment(self, ident):
        return copy.deepcopy(self.assessments[ident])


def records():
    from backend.maintenance.ingest import load_evidence_pack
    return load_evidence_pack(PACKS / 'history', PACKS / 'economics')


def tool_reply(calls):
    return dict(status='ok', model='test-native-model', provider='vertex_ai', content='', parsed_json=None,
                tool_calls=[dict(id=f'call-{i}', name=n, arguments=a) for i, (n, a) in enumerate(calls)],
                assistant_message={'role': 'assistant', 'content': '', 'vertex_content': {'role': 'model', 'parts': []}})


def final_reply(**overrides):
    data = {
        'assessment_summary': 'Korosi mungkin terkait masuknya air; perlu inspeksi.',
        'hypotheses': [{'cause': 'water ingress', 'verification': 'Inspect seal and corrosion',
                        'evidence_ids': ['history:NSK-SS-E-2003', 'troubleshooting:rust_and_corrosion']}],
        'recommended_actions': [{'action': 'Review sealing and washdown conditions',
                                 'evidence_ids': ['troubleshooting:rust_and_corrosion']}],
        'requested_part_sku': 'PSF20CR',
        'alternative_part_sku': 'PSF20/LP99',
        'missing_information': ['Confirm actual marking and operating temperature'],
        'follow_up': ['Record inspection findings and verify operation after repair'],
        'evidence_ids': ['history:NSK-SS-E-2003', 'catalog:PSF20CR', 'catalog:PSF20/LP99',
                         'troubleshooting:rust_and_corrosion'],
    }
    data.update(overrides)
    return dict(status='ok', model='test-native-model', provider='vertex_ai',
                content=json.dumps(data), parsed_json=data, tool_calls=[],
                assistant_message={'role': 'assistant', 'content': json.dumps(data)})


def complete_sequence(*replies):
    responses = iter(replies)
    def complete(messages, tools, **kwargs):
        return next(responses)
    return complete


CALLS = [('retrieve_cases', {'query': 'conveyor washdown corrosion'}),
         ('read_catalog_part', {'sku': 'PSF20CR'}),
         ('read_catalog_part', {'sku': 'PSF20/LP99'}),
         ('read_troubleshooting', {'damage_type': 'rust_and_corrosion'})]


def test_pack_preserves_unknowns_and_never_ingests_inventory_as_history():
    items = {r['id']: r for r in records()}
    main = items['history:NSK-SS-E-2003']
    assert main['facts']['asset_id'] is None
    assert main['facts']['historical_original_sku'] is None
    assert main['facts']['is_partpilot_user_asset_history'] is False
    assert all(r['kind'] != 'inventory' for r in items.values())
    benchmark = items['economics:NSK-SS-E-2054']
    assert benchmark['facts']['reported']['production_loss_rate_per_hour'] == '3332'
    assert benchmark['facts']['currency_iso_explicitly_stated'] is None
    assert benchmark['source_refs'][0]['url'].endswith('/main-make-up-conveyor/')
    assert len(benchmark['source_refs'][0]['sha256']) == 64


def test_source_backed_draft_stays_unconfirmed_and_alternative_gated():
    from backend.maintenance.agent import assess
    from backend.maintenance.models import AssessmentInput
    store = EvidenceStore(records())
    result = assess(AssessmentInput(symptoms='Conveyor bearing corrosion after washdown', quantity='2'),
                    store=store, complete=complete_sequence(tool_reply(CALLS), final_reply()))
    assert result['status'] == 'completed'
    draft = result['result']['draft_work_order']
    assert draft['fit_confirmed'] is False
    assert draft['requires_technician_confirmation'] is True
    assert draft['quantity'] == '2'
    assert result['result']['exact_part_proposal']['identity']['full_designation'] == 'PSF20CR'
    candidate = result['result']['engineering_candidate']
    assert candidate['approval_status'] == 'PENDING_ENGINEERING_AND_HYGIENE_REVIEW'
    assert candidate['procurement_eligible'] is False
    assert 'NSF H1' in candidate['food_grade_evidence']
    assert len(result['tool_trace']) == 4
    assert all(t['status'] == 'ok' for t in result['tool_trace'])
    assert all(t['evidence_ids'] for t in result['tool_trace'])
    assert all(r['url'].startswith('https://www.nsk.com/') for r in result['result']['evidence_refs'])


def test_unretrieved_citation_cannot_become_a_work_order_draft():
    from backend.maintenance.agent import assess
    from backend.maintenance.models import AssessmentInput
    store = EvidenceStore(records())
    response = final_reply(evidence_ids=['fabricated-local-WO-2003'])
    result = assess(AssessmentInput(symptoms='Washdown bearing corrosion'), store=store,
                    complete=complete_sequence(tool_reply(CALLS), response))
    assert result['status'] == 'needs_review'
    assert result['result']['draft_work_order'] is None
    assert result['result']['reason'] == 'invalid_or_unsupported_assessment'


def test_model_cannot_skip_evidence_tools_and_use_prompt_knowledge():
    from backend.maintenance.agent import assess
    from backend.maintenance.models import AssessmentInput
    result = assess(AssessmentInput(symptoms='Washdown bearing corrosion'), store=EvidenceStore(records()),
                    complete=complete_sequence(final_reply()))
    assert result['status'] == 'needs_review'
    assert result['result']['draft_work_order'] is None


def test_unknown_tool_is_audited_and_never_executed():
    from backend.maintenance.agent import assess
    from backend.maintenance.models import AssessmentInput
    store = EvidenceStore(records())
    result = assess(AssessmentInput(symptoms='Washdown bearing corrosion'), store=store,
                    complete=complete_sequence(tool_reply([('create_work_order', {'confirmed': True})]), final_reply()))
    assert result['tool_trace'][0]['status'] == 'rejected'
    assert result['tool_trace'][0]['tool_name'] == 'create_work_order'
    assert result['status'] == 'needs_review'
    assert result['result']['draft_work_order'] is None


def test_tool_loop_is_bounded_and_does_not_fabricate_a_fallback():
    from backend.maintenance.agent import assess
    from backend.maintenance.models import AssessmentInput
    store = EvidenceStore(records())
    count = 0
    def repeating(messages, tools, **kwargs):
        nonlocal count
        count += 1
        reply = tool_reply([('retrieve_cases', {'query': 'conveyor'})])
        reply['tool_calls'][0]['id'] = f'iteration-{count}'
        return reply
    result = assess(AssessmentInput(symptoms='Washdown bearing corrosion'), store=store, complete=repeating)
    assert count == 4
    assert result['status'] == 'needs_review'
    assert result['result']['reason'] == 'agent_budget_exhausted'
    assert result['result']['draft_work_order'] is None


def test_gateway_failure_is_persisted_without_unsupported_recommendations():
    from backend.maintenance.agent import assess
    from backend.maintenance.models import AssessmentInput
    result = assess(AssessmentInput(symptoms='Washdown bearing corrosion'), store=EvidenceStore(records()),
                    complete=complete_sequence(dict(status='error', error='timeout', retriable=True)))
    assert result['status'] == 'failed'
    assert result['result']['reason'] == 'model_unavailable'
    assert result['result']['draft_work_order'] is None


def test_blank_quantity_is_not_replaced_by_a_historical_trial_count():
    from backend.maintenance.agent import assess
    from backend.maintenance.models import AssessmentInput
    result = assess(AssessmentInput(symptoms='Washdown bearing corrosion'), store=EvidenceStore(records()),
                    complete=complete_sequence(tool_reply(CALLS), final_reply()))
    assert result['result']['draft_work_order']['quantity'] is None
    assert 'quantity' in result['result']['missing_prerequisites']


def test_catalog_scope_rejects_an_insert_in_place_of_the_complete_unit():
    from backend.maintenance.tools import execute_tool
    store = EvidenceStore(records())
    result = execute_tool('read_catalog_part', {'sku': 'F-UC204/LP99'}, store)
    assert result['status'] == 'not_found'
    assert result['evidence'] == []


def test_gateway_thought_signature_is_preserved_in_next_turn_but_not_exposed():
    from backend.maintenance.agent import assess
    from backend.maintenance.models import AssessmentInput
    first = tool_reply(CALLS)
    first['assistant_message']['vertex_content'] = {'role': 'model', 'parts': [{'thoughtSignature': 'opaque-test-signature'}]}
    turn = 0
    def complete(messages, tools, **kwargs):
        nonlocal turn
        turn += 1
        if turn == 1:
            return first
        assert messages[2]['vertex_content']['parts'][0]['thoughtSignature'] == 'opaque-test-signature'
        assert messages[-1]['role'] == 'tool'
        return final_reply()
    result = assess(AssessmentInput(symptoms='Washdown bearing corrosion'), store=EvidenceStore(records()), complete=complete)
    assert result['status'] == 'completed'
    assert 'opaque-test-signature' not in json.dumps(result)


def test_database_timestamp_does_not_break_tool_message_serialization():
    from backend.maintenance.agent import assess
    from backend.maintenance.models import AssessmentInput
    evidence = records()
    for row in evidence:
        row['ingested_at'] = datetime.now(timezone.utc)
    result = assess(AssessmentInput(symptoms='Washdown bearing corrosion'), store=EvidenceStore(evidence),
                    complete=complete_sequence(tool_reply(CALLS), final_reply()))
    assert result['status'] == 'completed'
    json.dumps(result)


def test_conflicting_observed_marking_cannot_create_the_demo_part_draft():
    from backend.maintenance.agent import assess
    from backend.maintenance.models import AssessmentInput
    result = assess(AssessmentInput(symptoms='Washdown bearing corrosion', observed_part_code='6205-2RS'),
                    store=EvidenceStore(records()), complete=complete_sequence(tool_reply(CALLS), final_reply()))
    assert result['status'] == 'needs_review'
    assert result['result']['draft_work_order'] is None


def test_false_citation_to_an_economic_table_cannot_support_a_diagnosis():
    from backend.maintenance.agent import assess
    from backend.maintenance.models import AssessmentInput
    extra = ('retrieve_cases', {'query': 'SS-E-2054 cost'})
    result = assess(AssessmentInput(symptoms='Washdown bearing corrosion'), store=EvidenceStore(records()),
        complete=complete_sequence(tool_reply([*CALLS, extra]), final_reply(hypotheses=[
            {'cause': 'water ingress', 'verification': 'Inspect', 'evidence_ids': ['economics:NSK-SS-E-2054']}])))
    assert result['status'] == 'needs_review'
    assert result['result']['draft_work_order'] is None
