"""Shared one-round negotiation: DB freezes a validated full-cost comparison."""
from . import repository as repo
from datetime import datetime,timezone,timedelta
import uuid

def available():
    return repo.query("SELECT to_regclass('pp.demo_negotiation_round') IS NOT NULL ready")[0]['ready']

def view(run_id):
    if not available():return None
    rows=repo.query('SELECT run_id,policy,round,best_option_id,best_total::text,target_total::text,created_at AS basis_at,basis FROM pp.demo_negotiation_round WHERE run_id=%s',(run_id,))
    if not rows:return None
    row=rows[0];basis=row.pop('basis')
    best=next(o for o in basis['eligible_complete_options'] if o['option_id']==row['best_option_id'])
    expired=datetime.fromisoformat(best['valid_until'])<=datetime.now(timezone.utc)
    plans=repo.query("SELECT p.vendor_id,p.status,p.reason,p.target_unit_price::text,p.quote,r.response->'quote' current_quote,e.id counter_id FROM pp.demo_negotiation_vendor p LEFT JOIN pp.demo_outbox r ON r.run_id=p.run_id AND r.vendor_id=p.vendor_id AND r.kind='rfq' LEFT JOIN pp.demo_outbox e ON e.run_id=p.run_id AND e.vendor_id=p.vendor_id AND e.kind='price_counteroffer' WHERE p.run_id=%s ORDER BY p.vendor_id",(run_id,))
    for p in plans:
        quote=p.pop('quote');current=p.pop('current_quote');counter=p.pop('counter_id')
        if p['status']=='planned' and not counter:
            reason=('benchmark_expired' if expired else 'quote_changed_before_negotiation' if current!=quote else 'expired_quote' if datetime.fromisoformat(quote['valid_until'])<=datetime.now(timezone.utc) else None)
            if reason:p.update(status='skipped',reason=reason,target_unit_price=None)
    return {**row,'vendors':plans}

def plan(run_id):
    from backend.wo.repository import get_db_connection
    with get_db_connection() as lock:
        lock.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',('negotiation:'+run_id,))
        return plan_locked(run_id)

def plan_locked(run_id):
    from .service import get_run
    from .comparison import create_comparison
    from backend.demo.console import default_comparison
    run=get_run(run_id)
    if run['decision'] or run['status']!='sourcing':return view(run_id)
    # No new comparison/round for already planned vendors. Incomplete vendors
    # can join the same frozen round once their quote becomes complete.
    old=view(run_id)
    planned={v['vendor_id'] for v in (old or {}).get('vendors',[])}
    if not any(v['eligible'] and v['vendor_id'] not in planned for v in run['vendors']):return old
    prefix=f"negotiation-{run_id}-{run['version']}-"
    rows=repo.query('SELECT id,created_at FROM pp.demo_comparison WHERE run_id=%s AND starts_with(request_key,%s) ORDER BY created_at DESC LIMIT 1',(run_id,prefix))
    if rows and rows[0]['created_at']>datetime.now(timezone.utc)-timedelta(seconds=55):
        comparison_id=rows[0]['id']
    else:
        comparison_id=create_comparison(run_id,default_comparison(run),prefix+uuid.uuid4().hex)['id']
    repo.call('demo_plan_negotiation',comparison_id)
    return view(run_id)
