from datetime import datetime, timedelta, timezone
import pytest
from backend.wo.models import EconomicOption


def option(hours=8):
    start = datetime(2026, 10, 23, tzinfo=timezone.utc)
    end = start + timedelta(hours=hours)
    def cost(key, amount, kind):
        return dict(cost_id=key,cost_type=kind,amount=dict(value=amount,unit='IDR',source='synthetic:test',assumption_version='1'),evidence_ref=key,description=key)
    return EconomicOption.model_validate(dict(option_id='test', costs_nonduplicated=True,
        donor_cost_status=dict(status='not_applicable',source='synthetic:surplus',assumption_version='1'),
        sourcing_costs=[cost('parts','100','sourcing')], incremental_disruption_costs=[cost('repair','20','recovery')],
        schedule=dict(future_from=start.isoformat(),horizon_end=(start+timedelta(hours=24)).isoformat(),calendar_source='synthetic:continuous',parallel_assumption_version='1',
            stages=[dict(id=k,kind=k,start=(start if k=='transport' else end).isoformat(),end=end.isoformat(),depends_on=[],source='synthetic',assumption_version='1') for k in ['procurement','dispatch','transport','installation','restart']],
            scheduled_impacted_windows=[dict(start=start.isoformat(),end=(start+timedelta(hours=24)).isoformat())])))


def test_external_rate_needs_explicit_conversion_and_applicability():
    from backend.procurement.benchmark import ReportedDowntimeBenchmark, calculate_benchmark
    result = calculate_benchmark(ReportedDowntimeBenchmark(), option())
    assert result['status'] == 'incomplete'
    assert result['published_unit_production_loss'] == '26656'
    assert result['future_relevant_option_total'] is None
    assert result['source_currency_iso'] is None


def test_benchmark_is_not_contribution_margin_and_keeps_synthetic_mapping():
    from backend.procurement.benchmark import ReportedDowntimeBenchmark, calculate_benchmark
    model=ReportedDowntimeBenchmark(external_applicability_acknowledged=True,
        idr_per_published_currency_unit='2',conversion_assumption_acknowledged=True)
    result=calculate_benchmark(model,option())
    assert result['estimated_production_loss'] == '53312.00'
    assert result['future_relevant_option_total_unrounded'] == '53432'
    assert result['unrecoverable_lost_contribution'] is None
    assert 'currency_mapping_is_simulation' in result['flags']


def test_only_future_scheduled_hours_count():
    from backend.procurement.benchmark import ReportedDowntimeBenchmark, calculate_benchmark
    opt=option()
    opt.schedule.scheduled_impacted_windows[0].start='2026-10-23T06:00:00+00:00'
    result=calculate_benchmark(ReportedDowntimeBenchmark(),opt)
    assert result['effective_scheduled_impacted_hours']=='2'
    assert result['published_unit_production_loss']=='6664'


def test_nonpositive_conversion_is_rejected():
    from backend.procurement.benchmark import ReportedDowntimeBenchmark
    with pytest.raises(ValueError): ReportedDowntimeBenchmark(idr_per_published_currency_unit='0')


def test_claimed_included_donor_cost_requires_an_explicit_charge():
    from backend.procurement.benchmark import ReportedDowntimeBenchmark, calculate_benchmark
    model = ReportedDowntimeBenchmark(external_applicability_acknowledged=True,
        idr_per_published_currency_unit='2', conversion_assumption_acknowledged=True)
    opt = option()
    opt.donor_cost_status.status = 'included'
    result = calculate_benchmark(model, opt)
    assert result['status'] == 'incomplete'
    assert '/donor_cost_status/included_cost' in result['missing_inputs']
    assert result['future_relevant_option_total'] is None


@pytest.mark.parametrize('kind', ['donor_opportunity', 'replenishment'])
def test_explicit_donor_charge_or_replenishment_satisfies_included_declaration(kind):
    from backend.procurement.benchmark import ReportedDowntimeBenchmark, calculate_benchmark
    model = ReportedDowntimeBenchmark(external_applicability_acknowledged=True,
        idr_per_published_currency_unit='2', conversion_assumption_acknowledged=True)
    opt = option()
    opt.donor_cost_status.status = 'included'
    opt.sourcing_costs[0].cost_type = kind
    result = calculate_benchmark(model, opt)
    assert result['status'] == 'complete_with_exclusions'
    assert result['future_relevant_option_total_unrounded'] == '53432'


def test_horizon_before_restoration_cannot_publish_a_complete_recovery_total():
    from backend.procurement.benchmark import ReportedDowntimeBenchmark, calculate_benchmark
    model = ReportedDowntimeBenchmark(external_applicability_acknowledged=True,
        idr_per_published_currency_unit='2', conversion_assumption_acknowledged=True)
    result = calculate_benchmark(model, option(hours=74))
    assert result['status'] == 'incomplete'
    assert '/schedule/horizon_end_before_restore' in result['missing_inputs']
    assert 'partial_horizon_not_full_recovery' in result['flags']
    assert result['elapsed_restore_hours'] == '74'
    assert result['effective_scheduled_impacted_hours'] == '24'
    assert result['published_unit_production_loss'] == '79968'
    assert result['estimated_production_loss'] is None
    assert result['future_relevant_option_total'] is None
    assert result['future_relevant_option_total_unrounded'] is None


def test_horizon_exactly_at_restoration_is_complete():
    from backend.procurement.benchmark import ReportedDowntimeBenchmark, calculate_benchmark
    model = ReportedDowntimeBenchmark(external_applicability_acknowledged=True,
        idr_per_published_currency_unit='2', conversion_assumption_acknowledged=True)
    result = calculate_benchmark(model, option(hours=24))
    assert result['status'] == 'complete_with_exclusions'
    assert result['effective_scheduled_impacted_hours'] == '24'
    assert result['future_relevant_option_total_unrounded'] == '160056'
