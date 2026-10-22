"""Exact complete-unit identity must survive extraction, sourcing, and quote validation."""
import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from backend.wo.identity import candidate_identity, same_identity
from backend.wo.matching import extract_facts_from_text, match_candidates
from backend.wo.availability import match_cross_warehouse_identity
from backend.wo.worker import validate_extraction
from backend.wo.models import Fact
from backend.procurement.models import Identity
from backend.whatsapp.extraction import validate_extraction as validate_vendor


CR = {'brand': 'RHP', 'base': 'PSF20', 'suffix': 'CR', 'manufacturer': 'RHP',
      'full_designation': 'PSF20CR', 'unit_scope': 'complete_housed_unit'}
LP99 = {'brand': 'RHP', 'base': 'PSF20', 'suffix': '/LP99', 'manufacturer': 'RHP',
        'full_designation': 'PSF20/LP99', 'unit_scope': 'complete_housed_unit'}


@pytest.mark.parametrize('label,expected', [('RHP PSF20CR', CR), ('rhp psf20/lp99', LP99)])
def test_complete_unit_label_retains_full_designation_and_scope(label, expected):
    assert candidate_identity({'item_name': label}) == expected


def test_catalog_brand_casing_is_normalized_without_changing_manufacturer():
    assert candidate_identity({'item_name': 'rhp psf20cr', 'brand': ' rhp '}) == CR
    assert candidate_identity({'item_name': 'ntn 6200llu', 'brand': 'ntn'}) == {
        'brand': 'NTN', 'base': '6200', 'suffix': 'LLU'}


def test_explicit_label_supplies_missing_catalog_brand_but_not_conflicting_brand():
    assert candidate_identity({'item_name': 'RHP PSF20CR', 'brand': None}) == CR
    assert candidate_identity({'item_name': 'NTN 6200LLU', 'brand': None}) == {
        'brand': 'NTN', 'base': '6200', 'suffix': 'LLU'}
    assert candidate_identity({'item_name': 'RHP PSF20CR', 'brand': 'NSK'}) is None


@pytest.mark.parametrize('label', ['RHP PSF20', 'RHP PSF20CR/C3', 'RHP PSF20/LP99D1',
                                   'NSK PSF20CR', 'RHP F-UC204/LP99', 'RHP PSF20CR C3'])
def test_unrecognized_or_partial_complete_unit_is_not_coerced(label):
    assert candidate_identity({'item_name': label}) is None


def test_complete_identity_cannot_be_downgraded_to_legacy_or_insert_scope():
    assert same_identity(CR, dict(CR))
    assert not same_identity(CR, LP99)
    assert not same_identity(CR, {k: CR[k] for k in ('brand', 'base', 'suffix')})
    assert not same_identity(CR, {**CR, 'unit_scope': 'bearing_insert'})
    assert not same_identity(CR, {**CR, 'full_designation': 'PSF20/LP99'})


def test_zero_stock_original_remains_identified_despite_available_upgrade():
    original = {'item_code': 'CR', 'item_name': 'RHP PSF20CR', 'brand': 'RHP', 'actual_qty': '0'}
    upgrade = {'item_code': 'LP', 'item_name': 'RHP PSF20/LP99', 'brand': 'RHP', 'actual_qty': '8'}
    text = 'bearing RHP PSF20CR'
    result = match_candidates([original, upgrade], extract_facts_from_text(text), input_text=text)
    assert result['state'] == 'identified'
    assert result['identified_candidate']['item_code'] == 'CR'
    assert match_cross_warehouse_identity(CR, upgrade, {}) == (False, 'identity_mismatch')
    assert match_cross_warehouse_identity(CR, original, {}) == (True, None)


def test_unknown_complete_designation_does_not_match_one_known_catalog_row():
    text = 'bearing RHP PSF20CR/C3'
    result = match_candidates([{'item_code': 'CR', 'item_name': 'RHP PSF20CR'}],
                              extract_facts_from_text(text), input_text=text)
    assert result['state'] == 'needs_review'
    assert result['identified_candidate'] is None


def test_explicit_complete_designation_survives_model_omission():
    valid, facts, reason = validate_extraction('{"facts": []}', 'bearing RHP PSF20/LP99', None, {})
    assert valid, reason
    assert any(f['key'] == 'full_designation' and f['value'] == 'PSF20/LP99' for f in facts)


@pytest.mark.parametrize('raw', ['bearing unit flange', 'bearing unit flange lengkap', 'bearing', 'laher'])
def test_grounded_bearing_unit_category_phrase_preserves_exact_evidence(raw):
    text = f'Ganti {raw} RHP PSF20CR'
    evidence = {'source_field': 'description', 'raw_substring': raw, 'normalized_value': 'Bearing'}
    fact = {'key': 'category', 'value': 'Bearing', 'source': 'description', 'evidence': [evidence]}
    valid, facts, reason = validate_extraction(json.dumps({'facts': [fact]}), text, None, {})
    assert valid, reason
    category = next(f for f in facts if f['key'] == 'category')
    assert category['value'] == 'Bearing'
    assert category['evidence'][0] == {**evidence, 'source_ref': None}
    result = match_candidates([{'item_code': 'CR', 'item_name': 'RHP PSF20CR', 'brand': 'RHP', 'actual_qty': '0'}],
                              [Fact(**f) for f in facts],
                              input_text=text)
    assert result['state'] == 'identified'
    assert result['identified_candidate']['item_code'] == 'CR'


@pytest.mark.parametrize('raw', ['load-bearing bracket', 'bearing-like unit', 'bukan bearing',
                                'seal untuk bearing', 'flange'])
def test_incidental_or_unsupported_phrase_cannot_become_bearing_category(raw):
    fact = {'key': 'category', 'value': 'Bearing', 'source': 'description',
            'evidence': [{'source_field': 'description', 'raw_substring': raw, 'normalized_value': 'Bearing'}]}
    valid, _, _ = validate_extraction(json.dumps({'facts': [fact]}), raw, None, {})
    assert not valid


def test_bearing_category_phrase_still_requires_verbatim_source_and_normalization():
    fact = {'key': 'category', 'value': 'Bearing', 'source': 'description',
            'evidence': [{'source_field': 'description', 'raw_substring': 'bearing unit flange',
                          'normalized_value': 'Bearing'}]}
    assert not validate_extraction(json.dumps({'facts': [fact]}), 'bearing RHP PSF20CR', None, {})[0]
    fact['value'] = 'Seal'
    assert not validate_extraction(json.dumps({'facts': [fact]}), 'bearing unit flange RHP PSF20CR', None, {})[0]


def test_model_cannot_crop_an_unsupported_designation_into_supported_code():
    fact = {'key': 'full_designation', 'value': 'PSF20CR', 'source': 'description',
            'evidence': [{'source_field': 'description', 'raw_substring': 'PSF20CR',
                          'normalized_value': 'PSF20CR'}]}
    valid, _, _ = validate_extraction(json.dumps({'facts': [fact]}), 'RHP PSF20CR/C3', None, {})
    assert not valid


def test_quote_identity_keeps_legacy_wire_shape_and_complete_contract():
    old = {'brand': 'NTN', 'base': '6200', 'suffix': 'LLU'}
    assert Identity(**old).model_dump(mode='json') == old
    assert Identity(**CR).model_dump(mode='json') == CR
    assert Identity(**LP99).model_dump(mode='json') == LP99
    for invalid in ({k: CR[k] for k in ('brand', 'base', 'suffix')},
                    {**CR, 'manufacturer': 'NSK'}, {**LP99, 'unit_scope': 'bearing_insert'},
                    {**CR, 'full_designation': 'PSF20/LP99'}):
        with pytest.raises(ValidationError):
            Identity(**invalid)


def test_vendor_evidence_retains_exact_original_and_upgrade_as_different_quotes():
    for text, expected in [('RHP PSF20CR', CR), ('RHP PSF20/LP99', LP99)]:
        result = validate_vendor({'fields': {'identity': {'raw': text}}}, text, datetime.now(timezone.utc))
        assert result['fields']['identity'] == expected
    text = 'RHP PSF20CR/C3'
    assert not validate_vendor({'fields': {'identity': {'raw': text}}}, text,
                               datetime.now(timezone.utc))['fields']


@pytest.mark.parametrize('text,raw', [('RHP PSF20CR/C3', 'RHP PSF20CR'),
                                    ('NTN 6200LLU/C3', 'NTN 6200LLU')])
def test_vendor_cropped_modifier_is_not_an_exact_quote(text, raw):
    result = validate_vendor({'fields': {'identity': {'raw': raw}}}, text, datetime.now(timezone.utc))
    assert 'identity' not in result['fields']
