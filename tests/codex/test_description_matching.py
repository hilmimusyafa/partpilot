"""Description-first behavior against explicit synthetic catalog evidence."""
import json

import pytest

from backend.wo.matching import extract_facts_from_text, match_candidates
from backend.wo.models import Fact
from backend.wo.worker import validate_extraction


WH1 = [
    dict(item_code='SYN-WH01-NTN-6200LLU', item_name='NTN 6200LLU', brand='NTN',
         description='USER-PROVIDED; MANUFACTURER-UNVERIFIED: 10x30x9 mm; LLU contact both sides'),
    dict(item_code='SYN-WH01-NTN-6801ZZ', item_name='NTN 6801ZZ', brand='NTN',
         description='USER-PROVIDED; MANUFACTURER-UNVERIFIED: 12x21x5 mm; ZZ metal shields both sides'),
]
WH2 = [
    dict(item_code='G2-BRG-017', item_name='LAHER ALUR 10X30X9 KARET RAPAT DUA SISI', brand='NTN',
         description='SIMULASI; label: NTN / 6200 / LLU; USER-PROVIDED; MANUFACTURER-UNVERIFIED'),
    dict(item_code='G2-BRG-018', item_name='LAHER ALUR 10X30X9 PLAT DUA SISI', brand='NTN',
         description='SIMULASI; label: NTN / 6200 / ZZ; USER-PROVIDED; MANUFACTURER-UNVERIFIED'),
    dict(item_code='G2-BRG-019', item_name='LAHER ALUR 10X30X9 KARET NONKONTAK DUA SISI', brand='NTN',
         description='SIMULASI; label: NTN / 6200 / LLB; USER-PROVIDED; MANUFACTURER-UNVERIFIED'),
]


def identify(text, rows=WH1, **kwargs):
    return match_candidates(rows, extract_facts_from_text(text), input_text=text, **kwargs)


@pytest.mark.parametrize('rows,code', [(WH1, 'SYN-WH01-NTN-6200LLU'), (WH2, 'G2-BRG-017')])
def test_description_selects_record_from_explicit_scoped_physical_metadata(rows, code):
    result = identify('bearing NTN 10x30x9 karet rapat dua sisi', rows)
    assert result['state'] == 'identified'
    assert result['identified_candidate']['item_code'] == code
    assert result['reason'] == 'scoped_physical_evidence_match'


def test_questions_request_observations_instead_of_unknown_codes():
    result = identify('bearing untuk motor conveyor')
    assert result['state'] == 'awaiting_clarification'
    assert {q.key for q in result['questions']} == {'brand', 'dimensions', 'seal_type'}


def test_unique_dimensions_and_closure_never_infer_brand():
    result = identify('bearing 10x30x9 karet rapat dua sisi')
    assert result['state'] == 'awaiting_clarification'
    assert [q.key for q in result['questions']] == ['brand']


def test_named_dimensions_and_natural_closure_preserve_verbatim_evidence():
    text = 'bearing NTN diameter dalam 10 mm, diameter luar 30 mm, lebar 9 mm, karet rapat di kedua sisi'
    facts = extract_facts_from_text(text)
    assert any(f.key == 'dimensions' and f.value == '10x30x9' for f in facts)
    assert any(f.key == 'seal_type' and f.value == 'contact_both_sides' for f in facts)
    valid, _, reason = validate_extraction(json.dumps({'facts': [f.model_dump() for f in facts]}), text, None, {})
    assert valid, reason
    assert identify(text)['state'] == 'identified'


def test_generic_rubber_requires_contact_observation_even_when_only_one_record():
    result = identify('bearing NTN 10x30x9 penutup karet dua sisi')
    assert result['state'] == 'awaiting_clarification'
    assert [q.key for q in result['questions']] == ['seal_type']


def test_noncontact_does_not_equate_llb_with_llf():
    result = identify('bearing NTN 10x30x9 karet nonkontak dua sisi', WH2)
    assert result['state'] == 'awaiting_clarification'
    assert [q.key for q in result['questions']] == ['suffix']


@pytest.mark.parametrize('extra', [dict(truncated=True), dict(clarification_round=3, truncated=True)])
def test_incomplete_retrieval_never_identifies_description(extra):
    result = identify('bearing NTN 10x30x9 karet rapat dua sisi', **extra)
    assert result['state'] != 'identified'


def test_unmapped_catalog_row_blocks_false_unique_physical_match():
    rows = WH1 + [dict(item_code='unknown', item_name='Bearing NTN', brand='NTN', description='No verified dimensions')]
    result = identify('bearing NTN 10x30x9 karet rapat dua sisi', rows)
    assert result['state'] == 'needs_review'
    assert result['reason'] == 'catalog_physical_metadata_incomplete'


def test_conflicting_observed_dimensions_are_not_discarded():
    result = identify('bearing NTN 10x30x9 atau 12x21x5 karet rapat dua sisi')
    assert result['state'] == 'needs_review'
    assert any(c['key'] == 'dimensions' for c in result['conflicts'])


def test_code_match_cannot_silently_ignore_conflicting_physical_evidence():
    result = identify('bearing NTN 6200 LLU ukuran 12x21x5')
    assert result['state'] != 'identified'


def test_description_clearance_modifier_cannot_be_discarded_without_mpn():
    result = identify('bearing NTN 10x30x9 karet rapat dua sisi C3')
    assert result['state'] == 'needs_review'
    assert result['reason'] == 'unsupported_designation_modifier'


def test_unavailable_scope_never_uses_other_warehouse_rules():
    assert identify('bearing NTN 10x30x9 karet rapat dua sisi', knowledge_status='knowledge_unavailable')['state'] == 'knowledge_unavailable'


def test_description_miss_is_not_an_arbitrary_catalog_choice():
    result = identify('bearing NTN 50x90x20 plat dua sisi')
    assert result['state'] == 'no_match'


def test_all_observations_exhausted_with_multiple_records_goes_to_review():
    result = identify('bearing NTN 10x30x9 karet rapat dua sisi', WH1 + [dict(WH1[0], item_code='duplicate')], clarification_round=3)
    assert result['state'] == 'needs_review'
    assert result['reason'] == 'clarification_rounds_exhausted'


def test_worker_retains_physical_observations_when_model_omits_them():
    text = 'bearing NTN 10x30x9 atau 12x21x5 karet rapat dua sisi'
    model_fact = dict(key='brand', value='NTN', source='description', evidence=[dict(
        source_field='description', raw_substring='NTN', normalized_value='NTN')])
    valid, facts, reason = validate_extraction(json.dumps({'facts': [model_fact]}), text, None, {})
    assert valid, reason
    result = match_candidates(WH1, [Fact(**f) for f in facts], input_text=text)
    assert result['state'] == 'needs_review'
    assert result['conflicts'][0]['key'] == 'dimensions'


def test_worker_retains_physical_answers_with_question_provenance():
    valid, facts, reason = validate_extraction('{"facts":[]}', 'bearing', None,
        {'q_dimensions_test': '10x30x9', 'q_seal_test': 'karet rapat di kedua sisi'})
    assert valid, reason
    assert {(f['key'], f['evidence'][0]['source_ref']) for f in facts} == {
        ('dimensions', 'q_dimensions_test'), ('seal_type', 'q_seal_test')}


@pytest.mark.parametrize('text', ['-10x30x9', '0.10x30x9', '10x30x9.5'])
def test_unsupported_dimension_formats_never_extract_partial_integer_size(text):
    assert not any(f.key == 'dimensions' for f in extract_facts_from_text(text))


def test_known_series_and_observed_contact_still_asks_measurements():
    result = identify('bearing NTN 6200 karet rapat dua sisi')
    assert result['state'] == 'awaiting_clarification'
    assert [q.key for q in result['questions']] == ['dimensions']


@pytest.mark.parametrize('text', ['bearing 0.10x30x9', 'bearing 10x30x9.5', 'bearing -10x30x9'])
def test_model_cannot_truncate_dimension_evidence_to_a_supported_integer_size(text):
    fact = dict(key='dimensions', value='10x30x9', source='description', evidence=[dict(
        source_field='description', raw_substring='10x30x9', normalized_value='10x30x9')])
    valid, _, reason = validate_extraction(json.dumps({'facts': [fact]}), text, None, {})
    assert not valid
    assert reason == 'dimensions_evidence_partial'


def test_live_technician_lubang_description_maps_without_requiring_code():
    text = 'Bearing conveyor merek NTN, lubang 10 mm, diameter luar 30 mm, lebar 9 mm, karet rapat dua sisi. Kode tidak terbaca.'
    raw_dimensions = 'lubang 10 mm, diameter luar 30 mm, lebar 9 mm'
    facts = [dict(key='brand', value='NTN', source='description', evidence=[dict(
        source_field='description', raw_substring='NTN', normalized_value='NTN')]),
        dict(key='dimensions', value='10x30x9', source='description', evidence=[dict(
        source_field='description', raw_substring=raw_dimensions, normalized_value='10x30x9')])]
    valid, extracted, reason = validate_extraction(json.dumps({'facts': facts}), text, None, {})
    assert valid, reason
    outcome = match_candidates(WH1, [Fact(**f) for f in extracted], input_text=text)
    assert outcome['state'] == 'identified'
    assert outcome['identified_candidate']['item_code'] == 'SYN-WH01-NTN-6200LLU'


@pytest.mark.parametrize('dimension_text', [
    'lubang 10 cm, diameter luar 30 mm, lebar 9 mm',
    'lubang 10.5 mm, diameter luar 30 mm, lebar 9 mm',
    'lubang -10 mm, diameter luar 30 mm, lebar 9 mm',
])
def test_lubang_named_measurements_do_not_convert_unsupported_units_or_decimal_sizes(dimension_text):
    assert not any(f.key == 'dimensions' for f in extract_facts_from_text(dimension_text))


def test_rule_first_complete_description_never_calls_gateway_and_reports_its_real_engine(monkeypatch):
    from backend.wo import worker
    monkeypatch.setenv('PARTPILOT_BEARING_RULE_FIRST', 'true')
    monkeypatch.setattr(worker.gateway, 'call_gateway_completion', lambda *a, **k: pytest.fail('gateway called for grounded rules'))
    facts = worker.prepare_rule_first_extraction('bearing NTN 10x30x9 karet rapat dua sisi', '', {}, WH1, False, 'available', 0)
    assert facts is not None
    result, elapsed, audit = worker.execute_extraction([], facts)
    assert result['status'] == 'ok'
    assert audit == dict(extraction_method='deterministic', gateway_called=False,
        requested_model=None, reported_model='deterministic-bearing-v1', timeout=None, max_tokens=None)
    assert elapsed >= 0


@pytest.mark.parametrize('text', ['bearing 10x30x9 karet rapat dua sisi',
    'bearing NTN 10x30x9 penutup karet dua sisi', 'bearing NTN 10x30x9 karet rapat dua sisi C3',
    'bearing bukan NTN 10x30x9 karet rapat dua sisi', 'bearing NTN 10x30x9 karet rapat dua sisi qty 2',
    'bearing NTN 50x90x20 plat dua sisi'])
def test_rule_first_ambiguous_unsupported_or_quantity_text_uses_gateway(monkeypatch, text):
    from backend.wo import worker
    monkeypatch.setenv('PARTPILOT_BEARING_RULE_FIRST', 'true')
    calls = []
    def complete(*args, **kwargs):
        calls.append(kwargs)
        return dict(status='ok', content='{"facts":[]}', model='test-gateway')
    monkeypatch.setattr(worker.gateway, 'call_gateway_completion', complete)
    facts = worker.prepare_rule_first_extraction(text, '', {}, WH1, False, 'available', 0)
    assert facts is None
    result, _, audit = worker.execute_extraction([], facts)
    assert len(calls) == 1 and audit['gateway_called'] is True
    assert result['model'] == 'test-gateway'


def test_rule_first_default_off_and_truncated_or_unavailable_catalog_never_bypasses(monkeypatch):
    from backend.wo import worker
    text = 'bearing NTN 10x30x9 karet rapat dua sisi'
    monkeypatch.delenv('PARTPILOT_BEARING_RULE_FIRST', raising=False)
    assert worker.prepare_rule_first_extraction(text, '', {}, WH1, False, 'available', 0) is None
    monkeypatch.setenv('PARTPILOT_BEARING_RULE_FIRST', 'true')
    assert worker.prepare_rule_first_extraction(text, '', {}, WH1, True, 'available', 0) is None
    assert worker.prepare_rule_first_extraction(text, '', {}, WH1, False, 'knowledge_unavailable', 0) is None


@pytest.mark.parametrize('unit', ['cm', 'm', 'inch', 'inci', 'inches', '"'])
def test_non_mm_dimension_unit_is_not_cropped_from_source_or_model_evidence(unit):
    text = f'bearing NTN 10x30x9 {unit} karet rapat dua sisi'
    assert not any(f.key == 'dimensions' for f in extract_facts_from_text(text))
    fact = dict(key='dimensions', value='10x30x9', source='description', evidence=[dict(
        source_field='description', raw_substring='10x30x9', normalized_value='10x30x9')])
    valid, _, reason = validate_extraction(json.dumps({'facts': [fact]}), text, None, {})
    assert not valid
    assert reason == 'dimensions_evidence_partial'


@pytest.mark.parametrize('uncertainty', ['sepertinya', 'kayaknya', 'kemungkinan', 'agaknya', 'belum pasti', 'sekitar'])
def test_rule_first_requires_unqualified_observations(monkeypatch, uncertainty):
    from backend.wo import worker
    monkeypatch.setenv('PARTPILOT_BEARING_RULE_FIRST', 'true')
    text = f'bearing {uncertainty} NTN 10x30x9 karet rapat dua sisi'
    assert worker.prepare_rule_first_extraction(text, '', {}, WH1, False, 'available', 0) is None


def test_rule_first_rejects_centimetres_but_accepts_explicit_millimetres(monkeypatch):
    from backend.wo import worker
    monkeypatch.setenv('PARTPILOT_BEARING_RULE_FIRST', 'true')
    assert worker.prepare_rule_first_extraction('bearing NTN 10x30x9 cm karet rapat dua sisi', '', {}, WH1, False, 'available', 0) is None
    assert worker.prepare_rule_first_extraction('bearing NTN 10x30x9 mm karet rapat dua sisi', '', {}, WH1, False, 'available', 0) is not None


def test_unsupported_dimension_units_block_exact_identity_even_when_model_omits_dimensions():
    text = 'bearing NTN 6200 LLU ukuran 10x30x9 cm'
    facts = [Fact(key=k, value=v, source='description', evidence=[]) for k, v in
             [('brand', 'NTN'), ('base', '6200'), ('suffix', 'LLU')]]
    result = match_candidates(WH1, facts, input_text=text)
    assert result['state'] == 'needs_review'
    assert result['reason'] == 'unsupported_dimension_unit'


@pytest.mark.parametrize('raw_evidence', ['10x30x9 mm', '10x30x9'])
def test_clarification_dimension_answer_accepts_explicit_mm_with_verbatim_evidence(raw_evidence):
    answers = {'q_dimensions_test': '10x30x9 mm'}
    fact = dict(key='dimensions', value='10x30x9', source='answer', evidence=[dict(
        source_field='answer', source_ref='q_dimensions_test', raw_substring=raw_evidence, normalized_value='10x30x9')])
    valid, facts, reason = validate_extraction(json.dumps({'facts': [fact]}), 'bearing', None, answers)
    assert valid, reason
    assert facts[0]['evidence'][0]['source_ref'] == 'q_dimensions_test'


def test_unknown_code_description_can_use_complete_observable_clarification(monkeypatch):
    from backend.wo import worker
    monkeypatch.setenv('PARTPILOT_BEARING_RULE_FIRST', 'true')
    description = 'Bearing conveyor bunyi, perlu diganti. Saya tidak tahu kodenya.'
    answers = {'q_brand_test': 'NTN', 'q_dimensions_test': '10x30x9 mm', 'q_seal_type_test': 'karet rapat dua sisi'}
    facts = worker.prepare_rule_first_extraction(description, '', answers, WH1, False, 'available', 1)
    assert facts is not None
    result = match_candidates(WH1, [Fact(**f) for f in facts], input_text=description+'\n'+'\n'.join(answers.values()))
    assert result['state'] == 'identified'
    assert result['identified_candidate']['item_code'] == 'SYN-WH01-NTN-6200LLU'
    assert {f['evidence'][0]['source_ref'] for f in facts} == set(answers)


def test_uncertain_brand_is_not_treated_as_merely_unknown_code(monkeypatch):
    from backend.wo import worker
    monkeypatch.setenv('PARTPILOT_BEARING_RULE_FIRST', 'true')
    description = 'Bearing conveyor bunyi. Saya tidak tahu mereknya.'
    answers = {'brand': 'NTN', 'dimensions': '10x30x9 mm', 'seal': 'karet rapat dua sisi'}
    assert worker.prepare_rule_first_extraction(description, '', answers, WH1, False, 'available', 1) is None


@pytest.mark.parametrize('description,expected_state,calls_expected', [
    ('Bearing conveyor merek NTN, lubang 10 mm, diameter luar 30 mm, lebar 9 mm, karet rapat dua sisi. Kode tidak terbaca.', 'identified', 0),
    ('bearing NTN', 'awaiting_clarification', 1),
])
def test_persisted_rule_first_worker_uses_honest_audit_and_real_call_budget(monkeypatch, description, expected_state, calls_expected):
    import uuid
    from isolated import Cluster
    from backend.wo import worker
    db = Cluster()
    try:
        monkeypatch.setenv('TEST_DATABASE_URL', db.dsn)
        monkeypatch.setenv('PARTPILOT_BEARING_RULE_FIRST', 'true')
        calls = []
        def complete(*args, **kwargs):
            calls.append(kwargs)
            return dict(status='ok', content='{"facts":[]}', model='controlled-test')
        monkeypatch.setattr(worker.gateway, 'call_gateway_completion', complete)
        draft = db.draft(description, quantity='12')
        submitted = db.api('POST', f"/api/v1/work-orders/{draft['id']}/submit",
            dict(expected_version=draft['version']), uuid.uuid4().hex)
        assert submitted['status'] == 202
        worker.process_job(worker.claim_next_job('rule-first-test'))
        row = db.row(draft['id'])
        assert row['state'] == expected_state
        assert len(calls) == calls_expected
        events = db.sql('SELECT event_type,payload FROM pp.wo_identification_event WHERE session_id=%s ORDER BY seq', (draft['id'],))
        assert sum(e['event_type'] == 'gateway_call_reserved' for e in events) == calls_expected
        result = next(e['payload'] for e in reversed(events) if e['event_type'] == 'result_applied')
        if calls_expected == 0:
            assert result['extraction_method'] == 'deterministic'
            assert result['requested_model'] is None
            assert result['reported_model'] == 'deterministic-bearing-v1'
            assert result['ordinal'] is None and result['max_tokens'] is None and result['timeout'] is None
            assert result['gateway_called'] is False and result['response_sha256'] is None
            assert row['result']['extraction']['extraction_method'] == 'deterministic'
            assert row['result']['identified_item_code'] == 'SYN-WH01-NTN-6200LLU'
        else:
            assert result['extraction_method'] == 'model' and result['gateway_called'] is True
            assert result['reported_model'] == 'controlled-test'
    finally:
        db.close()


def test_persisted_clarification_answers_identify_without_a_second_gateway_call(monkeypatch):
    import uuid
    from isolated import Cluster
    from backend.wo import worker
    db = Cluster()
    try:
        monkeypatch.setenv('TEST_DATABASE_URL', db.dsn)
        monkeypatch.setenv('PARTPILOT_BEARING_RULE_FIRST', 'true')
        monkeypatch.setattr(worker.gateway, 'call_gateway_completion',
            lambda *args, **kwargs: dict(status='ok', content='{"facts":[]}', model='controlled-initial-extraction'))
        draft = db.draft('Bearing conveyor bunyi, perlu diganti. Saya tidak tahu kodenya.')
        submitted = db.api('POST', f"/api/v1/work-orders/{draft['id']}/submit",
            dict(expected_version=draft['version']), uuid.uuid4().hex)
        assert submitted['status'] == 202
        worker.process_job(worker.claim_next_job('clarification-initial'))
        row = db.row(draft['id'])
        assert row['state'] == 'awaiting_clarification'
        responses = {'brand': 'NTN', 'dimensions': '10x30x9 mm', 'seal_type': 'karet rapat dua sisi'}
        answers = [dict(question_id=q['id'], answer=responses[q['key']]) for q in row['result']['questions']]
        answered = db.api('POST', f"/api/v1/work-orders/{draft['id']}/answers",
            dict(expected_version=row['version'], answers=answers), uuid.uuid4().hex)
        assert answered['status'] == 202
        monkeypatch.setattr(worker.gateway, 'call_gateway_completion',
            lambda *args, **kwargs: pytest.fail('complete clarification must use grounded rules'))
        worker.process_job(worker.claim_next_job('clarification-complete'))
        row = db.row(draft['id'])
        assert row['state'] == 'identified'
        assert row['result']['identified_item_code'] == 'SYN-WH01-NTN-6200LLU'
        assert row['result']['extraction']['gateway_called'] is False
        assert {f['evidence'][0]['source_ref'] for f in row['result']['facts']} == {a['question_id'] for a in answers}
        events = db.sql("SELECT count(*) n FROM pp.wo_identification_event WHERE session_id=%s AND event_type='gateway_call_reserved'", (draft['id'],))
        assert events[0]['n'] == 1
    finally:
        db.close()
