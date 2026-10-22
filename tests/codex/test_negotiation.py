"""Frozen whole-cost budget, replay boundaries and private outbound payloads."""
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
import uuid
import sys
import pytest
sys.path.insert(0,str(Path(__file__).parent))
from test_whatsapp import wa as ng

def initial_quotes(c,price_override=None):
    from test_procurement import start
    from backend.procurement import repository as repo,service
    from backend.procurement.simulator import DemoSimulator
    run=start(c,qty='6',origin='SYN-WH-01',code='SYN-WH01-NTN-6200LLU')
    payload={k:run[k] for k in ('identity','quantity','destination_warehouse_id','requested_at','expires_at')}
    payload['currency']='IDR'
    class Prices(DemoSimulator):
        def send(self,event):
            response=super().send(event)
            if price_override and event['vendor_id'] in price_override and response.quote:
                response.quote.unit_price=price_override[event['vendor_id']]
            return response
    for vendor in ('SIM-ENOUGH','SIM-SHORT','SIM-REFUSE','SIM-REVISE','SIM-SILENT'):
        event=repo.call('demo_enqueue',run['id'],vendor,'rfq',payload)
        service.deliver(event,Prices())
    return run,payload

@pytest.mark.parametrize('override,best,total,target',[({},'vendor:SIM-ENOUGH','1170000','1053000'),({'SIM-ENOUGH':'160000'},'warehouse:SYN-WH-02','1190000','1071000')])
def test_best_warehouse_or_vendor_controls_exact_total_budget(ng,override,best,total,target):
    from backend.procurement.negotiation import plan
    from backend.procurement.service import advance
    run,_=initial_quotes(ng,override)
    basis=plan(run['id'])
    assert basis['best_option_id']==best
    assert Decimal(basis['best_total'])==Decimal(total)
    assert Decimal(basis['target_total'])==Decimal(target)
    rows=ng.sql('SELECT * FROM pp.demo_negotiation_vendor WHERE run_id=%s',(run['id'],))
    assert len(rows)==3
    for r in rows:
        assert r['target_unit_price']*6+r['non_item_total']<=Decimal(target)
        assert (r['target_unit_price']+1)*6+r['non_item_total']>Decimal(target)
    first=advance(run['id']);again=advance(run['id'])
    assert len([e for e in first['exchanges'] if e['kind']=='price_counteroffer'])==3
    assert first['exchanges']==again['exchanges']
    assert ng.sql('SELECT count(*) n FROM pp.demo_negotiation_round')[0]['n']==1
    assert all('best_total' not in e['payload'] and 'non_item_total' not in e['payload'] for e in first['exchanges'])

def test_continuous_shift_unachievable_target_skips_without_fake_negative_offer(ng):
    from backend.procurement.service import get_run,advance
    from backend.demo.console import default_comparison
    from backend.procurement.comparison import create_comparison
    from backend.procurement import repository as repo
    from backend.procurement.negotiation import view
    run,_=initial_quotes(ng);current=get_run(run['id']);body=default_comparison(current)
    for o in body.options:
        o.schedule.scheduled_impacted_windows[0].start=o.schedule.future_from
    comp=create_comparison(run['id'],body,uuid.uuid4().hex)
    repo.call('demo_plan_negotiation',comp['id'])
    result=view(run['id'])
    assert result['best_option_id']=='warehouse:SYN-WH-02'
    assert all(v['status']=='skipped' and v['reason']=='non_item_cost_exceeds_target' for v in result['vendors'])
    assert not [e for e in advance(run['id'])['exchanges'] if e['kind']=='price_counteroffer']

def test_crash_after_comparison_and_concurrent_planning_reuses_frozen_request(ng,monkeypatch):
    from backend.procurement.negotiation import plan
    from backend.procurement import repository as repo
    from concurrent.futures import ThreadPoolExecutor
    run,_=initial_quotes(ng);original=repo.call
    def crash(name,*args):
        if name=='demo_plan_negotiation':raise RuntimeError('owned crash after persisted comparison')
        return original(name,*args)
    monkeypatch.setattr(repo,'call',crash)
    with pytest.raises(RuntimeError):plan(run['id'])
    monkeypatch.setattr(repo,'call',original)
    with ThreadPoolExecutor(max_workers=3) as ex:results=list(ex.map(lambda _:plan(run['id']),range(3)))
    assert all(r['best_total']==results[0]['best_total'] for r in results)
    assert ng.sql('SELECT count(*) n FROM pp.demo_comparison')[0]['n']==1
    assert ng.sql('SELECT count(*) n FROM pp.demo_negotiation_round')[0]['n']==1

def test_db_rejects_arbitrary_target_and_changed_terms_become_skipped(ng):
    from backend.procurement.negotiation import plan
    from backend.procurement import repository as repo
    from backend.procurement.service import advance
    run,payload=initial_quotes(ng);plan(run['id'])
    with pytest.raises(Exception,match='negotiation_plan_mismatch'):
        repo.call('demo_enqueue',run['id'],'SIM-ENOUGH','price_counteroffer',dict(payload,target_unit_price='1'))
    ng.sql("UPDATE pp.demo_outbox SET response=jsonb_set(response,'{quote,shipping_amount}','\"35000\"') WHERE run_id=%s AND vendor_id='SIM-ENOUGH' AND kind='rfq'",(run['id'],))
    for _ in range(2):
        view=advance(run['id'])['negotiation']
        changed=next(v for v in view['vendors'] if v['vendor_id']=='SIM-ENOUGH')
        assert changed['status']=='skipped' and changed['reason']=='quote_changed_before_negotiation'
    assert not ng.sql("SELECT id FROM pp.demo_outbox WHERE vendor_id='SIM-ENOUGH' AND kind='price_counteroffer'")
