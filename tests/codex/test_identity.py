from backend.wo import availability
from backend.wo.models import Session, Fact
from backend.wo.matching import match_candidates

def test_alternative_search_uses_identified_6801_not_hardcoded_6200(monkeypatch):
    seen=[]
    def scope(warehouse, qty, identity, *args):
        seen.append(identity)
        return availability.AvailabilityScope(warehouse_id=warehouse,status='sufficient')
    monkeypatch.setattr(availability,'evaluate_scope',scope)
    s=Session(id='x',company_id='c',warehouse_id='w',state='identified',version=2,
              quantity='1',result={'identified_candidate':{'item_name':'NTN 6801ZZ','brand':'NTN'}})
    availability.evaluate_availability(s)
    assert seen[0]['base']=='6801' and seen[0]['suffix']=='ZZ'

def test_missing_suffix_cannot_select_single_catalog_candidate():
    rows=[{'item_code':'a','item_name':'NTN 6200LLU','brand':'NTN'}]
    facts=[Fact(key=k,value=v,source='description',evidence=[]) for k,v in [('brand','NTN'),('base','6200')]]
    result=match_candidates(rows,facts)
    assert result['state']=='awaiting_clarification'
    assert not result['identified_candidate']

def test_additional_designation_modifiers_are_not_discarded():
    from backend.wo.identity import candidate_identity,has_unsupported_modifier
    for label in ('NTN 6200LLU/C3','NTN 6200LLU-C3','NTN 6200LLU C3',
                  'bearing NTN 6200, suffix belum diketahui\nLLU/C3'):
        assert candidate_identity({'item_name':label}) is None
        assert has_unsupported_modifier(label)
        facts=[Fact(key=k,value=v,source='description',evidence=[]) for k,v in [('brand','NTN'),('base','6200'),('suffix','LLU')]]
        result=match_candidates([{'item_code':'a','item_name':'NTN 6200LLU','brand':'NTN'}],facts,input_text=label)
        assert result['state']=='needs_review'

def test_llh_is_a_supported_explicit_closure():
    import json
    from backend.wo.worker import validate_extraction
    fact=dict(key='suffix',value='LLH',source='description',evidence=[dict(source_field='description',raw_substring='LLH',normalized_value='LLH')])
    assert validate_extraction(json.dumps({'facts':[fact]}),'NTN 6000LLH',None,{})[0]

def test_conflicting_closures_remain_visible_for_review():
    facts=[Fact(key='suffix',value=v,source='description',evidence=[]) for v in ('LLU','ZZ')]
    result=match_candidates([{'item_code':'a','item_name':'NTN 6200LLU','brand':'NTN'}],facts)
    assert result['state']=='needs_review' and result['identified_candidate'] is None
    assert result['conflicts'][0]['values']==['LLU','ZZ']
