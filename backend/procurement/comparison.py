"""Immutable, qualified comparisons. Financial math is reused from the WO engine."""
from datetime import datetime, timedelta
from decimal import Decimal
from backend.wo.economics import calculate_option_economics, parse_rfc3339
from backend.wo.models import EconomicOption, EconomicCost, EconomicDatum
from .models import Quote
from . import repository as repo
from .service import get_run,now

def warehouse_quote(run,scope):
    # Explicit synthetic replenishment convention: restore donor ending stock.
    # No additional book-value charge. These are assumptions, not ERP prices.
    origin=scope['warehouse_id']==run['destination_warehouse_id']
    food=run['identity'].get('unit_scope')=='complete_housed_unit'
    candidate=run['identity'].get('full_designation')=='PSF20/LP99'
    return dict(quote_id=f"{run['id']}:{scope['warehouse_id']}",revision=1,identity=run['identity'],
                qty_available=scope.get('available_qty'),quantity_unit='Nos',unit_price=('4200000' if candidate else '3200000') if food else '150000',currency='IDR',
                shipping_amount='0' if origin else ('250000' if food else '40000'),tax_amount='0',processing_hours='0' if origin else '1',
                delivered_eta=(datetime.fromisoformat(run['requested_at'])+timedelta(hours=0 if origin else (4 if food else 2))).isoformat(),
                destination_warehouse_id=run['destination_warehouse_id'],valid_until=run['expires_at'],
                source='synthetic:replenishment-and-transfer-assumption',assumption_version='food-conveyor-v1' if food else 'bearing-mvp-v1')

def sources(run):
    result=[]
    for scope in [run['availability']['origin'],*run['availability']['alternatives']]:
        result.append({'source_kind':'warehouse','source_id':scope['warehouse_id'],'item_code':scope.get('item_code'),
                       'item_evidence':next(iter(scope.get('evidence') or []),None),
                       'quote':warehouse_quote(run,scope),'reasons':[] if scope['status']=='sufficient' else [scope['status']]})
    for vendor in run['vendors']:
        result.append({'source_kind':'vendor','source_id':vendor['vendor_id'],'quote':vendor['quote'],
                       'initial_quote':vendor['initial_quote'],'vendor_outcome':vendor['outcome'],
                       'reasons':vendor['ineligible_reasons']})
    return result

def read_comparison(cid, initial=False):
    row=repo.comparison_row(cid);at=row["created_at"] if initial else now()
    return {'api_version':'procurement-demo-v1','id':cid,'version':row['version'],'run_id':row['run_id'],
            **row['snapshot'],'historical_snapshot':True,'validity_checked_at':at.isoformat(),
            'unexpired_option_ids':[o['option_id'] for o in row['snapshot']['eligible_complete_options'] if datetime.fromisoformat(o['valid_until'])>at],
            'current_stock_revalidated':False,'procurement_executed':False}

def create_comparison(rid,body,key):
    request=body.model_dump(mode='json')
    old=repo.query('SELECT id,request,run_id FROM pp.demo_comparison WHERE request_key=%s',(key,))
    if old:
        if old[0]['run_id']!=rid or old[0]['request']!=request:raise repo.ProcurementError('idempotency_conflict','Key already used')
        return read_comparison(old[0]['id'], initial=True)
    run=get_run(rid);at=now()
    from .benchmark import ReportedDowntimeBenchmark
    food=run['identity'].get('unit_scope')=='complete_housed_unit'
    if food and not isinstance(body.production,ReportedDowntimeBenchmark):
        raise repo.ProcurementError('benchmark_acknowledgment_required','Food demo requires the explicit sourced benchmark mode',422)
    if isinstance(body.production,ReportedDowntimeBenchmark):
        stored=repo.query("SELECT facts FROM pp.maintenance_evidence WHERE id='economics:NSK-SS-E-2054'")
        if not stored or stored[0]['facts']['reported'].get('production_loss_rate_per_hour')!='3332':
            raise repo.ProcurementError('benchmark_evidence_missing','Verified published benchmark is missing',503)
    if run['version']!=body.expected_version:raise repo.ProcurementError('version_conflict','Run changed; refresh quotes')
    if body.production.currency!='IDR':raise repo.ProcurementError('incomparable_currency','Demo sources use IDR',422)
    all_sources=sources(run);assumptions={o.source_id:o for o in body.options}
    if set(assumptions)-{s['source_id'] for s in all_sources}:raise repo.ProcurementError('unknown_source','Source is not in this run',422)
    horizons={(o.schedule.future_from,o.schedule.horizon_end) for o in body.options}
    if len(horizons)>1:raise repo.ProcurementError('incomparable_horizon','Use the same horizon for every option',422)
    eligible=[];unrankable=[]
    for source in all_sources:
        option=dict(source,option_id=f"{source['source_kind']}:{source['source_id']}",quantity=run['quantity'])
        reasons=list(source['reasons']);q=source['quote'];a=assumptions.get(source['source_id'])
        if a is None:reasons.append('missing_recovery_assumptions')
        if q and datetime.fromisoformat(q['valid_until'])<=at:reasons.append('expired_quote')
        if reasons:
            option['reasons']=reasons;unrankable.append(option);continue
        quote=Quote.model_validate(q)
        schedule=a.schedule
        if abs((parse_rfc3339(schedule.future_from)-at).total_seconds())>60:
            raise repo.ProcurementError('invalid_schedule','future_from must represent comparison time (within 60 seconds)',422)
        # ETA is delivery, not restored production. Installation and restart
        # remain explicit; both must start no earlier than source arrival.
        eta=quote.delivered_eta
        if any(parse_rfc3339(stage.start)<eta for stage in schedule.stages if stage.kind in ('installation','restart')):
            raise repo.ProcurementError('invalid_schedule','Recovery cannot start before quoted arrival',422)
        transport_ends=[parse_rfc3339(s.end) for s in schedule.stages if s.kind=='transport']
        if not transport_ends or max(transport_ends)<eta:
            raise repo.ProcurementError('invalid_schedule','Transport schedule precedes quoted arrival',422)
        def cost(name,value,kind):
            return EconomicCost(cost_id='source:'+name,cost_type=kind,
                amount=EconomicDatum(value=value,unit='IDR',source=quote.source,assumption_version=quote.assumption_version),
                evidence_ref=f"{quote.quote_id}:{quote.revision}:{name}",description=name)
        acquisition=str(Decimal(run['quantity'])*Decimal(quote.unit_price))
        sourcing=[cost('parts_or_replenishment',acquisition,'replenishment' if source['source_kind']=='warehouse' else 'sourcing'),
                  cost('shipping',quote.shipping_amount,'transfer' if source['source_kind']=='warehouse' else 'sourcing'),
                  cost('tax',quote.tax_amount,'sourcing')]
        if any(c.cost_type not in ('donor_opportunity',) for c in a.donor_costs):
            raise repo.ProcurementError('duplicate_cost','Only additional donor opportunity costs allowed; replenishment already included',422)
        economic=EconomicOption(option_id=option['option_id'],availability_snapshot_id=run['availability']['snapshot_id'],
                                costs_nonduplicated=True,donor_cost_status=a.donor_cost_status,schedule=schedule,
                                sourcing_costs=sourcing+a.donor_costs,incremental_disruption_costs=a.incremental_disruption_costs)
        try:
            from .benchmark import ReportedDowntimeBenchmark,calculate_benchmark
            result=(calculate_benchmark(body.production,economic) if isinstance(body.production,ReportedDowntimeBenchmark)
                    else calculate_option_economics(body.production,economic).model_dump(mode='json'))
        except ValueError as exc:raise repo.ProcurementError('invalid_economics',str(exc),422) from None
        option.update(valid_until=q['valid_until'],economics=result,assumptions=a.model_dump(mode='json'))
        if result['status']=='incomplete':
            option['reasons']=result['missing_inputs'];unrankable.append(option)
        else:eligible.append(option)
    eligible.sort(key=lambda o:(Decimal(o['economics']['future_relevant_option_total_unrounded']),o['source_kind'],o['source_id']))
    snapshot={'as_of':at.isoformat(),'source_run_version':run['version'],'production':body.production.model_dump(mode='json'),
              'eligible_complete_options':eligible,'unrankable_options':unrankable,
              'status':'comparison_available' if eligible else 'incomplete',
              'coverage_complete':run['availability']['complete'] and not unrankable,
              'tie_policy':'unrounded total, source_kind, source_id','simulated':True,
              'source_snapshot':run,'procurement_executed':False}
    cid=repo.call('demo_compare',rid,body.expected_version,key,request,snapshot)
    return read_comparison(cid, initial=True)
