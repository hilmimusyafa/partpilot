"""Explicit live-model smoke on the dedicated demo (creates synthetic WOs)."""
import argparse
import json
from pathlib import Path
import time
import uuid
import httpx

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--url',default='http://127.0.0.1:18080')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--scenario',choices=['origin_stock','transfer_alias','vendor_purchase','clarification'])
    args=parser.parse_args()
    values=dict(line.split('=',1) for line in Path('/home/rifqisetiawan/.config/partpilot/demo-runtime.env').read_text().splitlines() if '=' in line)
    client=httpx.Client(base_url=args.url,auth=('demo',values['PARTPILOT_DEMO_PASSWORD']),timeout=30)
    config=client.get('/api/v1/demo/config').raise_for_status().json()
    client.headers.update({'X-PartPilot-Request':'demo','X-PartPilot-Generation':str(config['generation'])})
    def call(method,path,body=None,key=None):
        r=client.request(method,'/api/v1'+path,json=body,headers={'Idempotency-Key':key or uuid.uuid4().hex})
        assert r.status_code<300,(path,r.status_code,r.text[:500])
        return r.json()
    def wait(s):
        deadline=time.monotonic()+160
        while s['state'] in ('queued','processing') and time.monotonic()<deadline:
            time.sleep(1)
            s=call('GET',f"/work-orders/{s['id']}")
        return s
    results=[]
    for scenario in config['scenarios']:
        if args.scenario and scenario['id']!=args.scenario:continue
        body=dict(config['context'],warehouse_id=scenario['warehouse_id'],description=scenario['description'],quantity=scenario['quantity'])
        s=call('POST','/work-orders',body)
        s=wait(call('POST',f"/work-orders/{s['id']}/submit",{'expected_version':s['version']}))
        if scenario['id']=='clarification':
            assert s['state']=='awaiting_clarification',s
            for _ in range(3):
                answers=[]
                for q in s['questions']:
                    answer={'brand':'NTN','base':'6200','suffix':'LLU','category':'Bearing','quantity':'1'}.get(q['key'],'NTN 6200LLU')
                    answers.append({'question_id':q['id'],'answer':answer})
                s=wait(call('POST',f"/work-orders/{s['id']}/answers",{'expected_version':s['version'],'answers':answers}))
                if s['state']!='awaiting_clarification':break
        assert s['state']=='identified',(scenario['id'],s)
        run=call('POST','/demo/sourcing-runs',{'session_id':s['id'],'expected_version':s['version']})
        run=call('POST',f"/demo/sourcing-runs/{run['id']}/advance",{})
        if scenario['id']=='origin_stock':assert run['vendors']==[] and run['status']=='fulfilled_source'
        if scenario['id']=='transfer_alias':
            wh2=next(w for w in run['availability']['alternatives'] if w['warehouse_id']=='SYN-WH-02')
            assert wh2['status']=='sufficient' and wh2['item_code']=='G2-BRG-017',wh2
        if scenario['id']=='vendor_purchase':
            outcomes={v['vendor_id']:v['outcome'] for v in run['vendors']}
            assert set(outcomes.values())=={'quoted','insufficient_stock','negotiation_refused','revised_quote','no_response'},outcomes
        comparison=call('POST',f"/demo/sourcing-runs/{run['id']}/prepare-comparison",{})
        option=comparison['eligible_complete_options'][0]
        if scenario['id']=='transfer_alias':assert option['source_id']=='SYN-WH-02',option
        decision=call('POST',f"/demo/comparisons/{comparison['id']}/decision",{'expected_version':1,'option_id':option['option_id'],'acknowledgment':'demo_only'})
        assert decision['procurement_executed'] is False
        results.append({'scenario':scenario['id'],'wo':s['id'],'run_id':run['id'],'comparison_id':comparison['id'],'selected':option['option_id'],'total':option['economics']['future_relevant_option_total'],'vendor_outcomes':{v['vendor_id']:v['outcome'] for v in run['vendors']}})
        if args.output:args.output.write_text(json.dumps(results,indent=2))
        print('PASS',scenario['id'],option['option_id'],flush=True)
    if args.output:args.output.write_text(json.dumps(results,indent=2))
    print(f'{len(results)} live-model scenarios passed; no procurement executed.')

if __name__=='__main__':main()
