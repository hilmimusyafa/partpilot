"""Published production-loss benchmark, not a fabricated contribution margin."""
from decimal import Decimal, ROUND_HALF_EVEN
from typing import Literal
from pydantic import BaseModel, ConfigDict, field_validator
from backend.wo.models import EconomicOption
from backend.wo.economics import evaluate_schedule, parse_rfc3339


class ReportedDowntimeBenchmark(BaseModel):
    model_config = ConfigDict(extra='forbid')
    mode: Literal['reported_downtime_rate'] = 'reported_downtime_rate'
    case_id: Literal['NSK-SS-E-2054'] = 'NSK-SS-E-2054'
    rate_per_hour: Literal['3332'] = '3332'
    published_currency_symbol: Literal['$'] = '$'
    source_currency_iso: None = None
    price_year: None = None
    currency: Literal['IDR'] = 'IDR'
    currency_scale: Literal[2] = 2
    external_applicability_acknowledged: bool = False
    idr_per_published_currency_unit: str | None = None
    conversion_assumption_acknowledged: bool = False
    conversion_basis: Literal['synthetic_demo_mapping_not_verified_fx'] = 'synthetic_demo_mapping_not_verified_fx'
    source_url: Literal['https://www.nsk.com/am-en/tools-resources/bearings/aip/success-stories-overview/main-make-up-conveyor/'] = 'https://www.nsk.com/am-en/tools-resources/bearings/aip/success-stories-overview/main-make-up-conveyor/'

    @field_validator('idr_per_published_currency_unit')
    @classmethod
    def positive_mapping(cls, value):
        if value is None: return value
        import re
        if not re.fullmatch(r'\d{1,12}(?:\.\d{1,6})?', value) or Decimal(value) <= 0:
            raise ValueError('positive explicit decimal currency mapping required')
        return value


def calculate_benchmark(benchmark: ReportedDowntimeBenchmark, option: EconomicOption) -> dict:
    elapsed, hours, restored, missing = evaluate_schedule(option.schedule)
    missing = list(missing or [])
    partial_horizon = bool(restored and parse_rfc3339(option.schedule.horizon_end) < parse_rfc3339(restored))
    if partial_horizon:
        missing.append('/schedule/horizon_end_before_restore')
    if not option.costs_nonduplicated: raise ValueError('nonduplicated costs required')
    costs = option.sourcing_costs + option.incremental_disruption_costs
    if len({c.cost_id for c in costs}) != len(costs) or len({c.evidence_ref for c in costs}) != len(costs):
        raise ValueError('duplicate cost')
    for c in costs:
        if c.amount.unit != 'IDR': raise ValueError('incomparable cost currency')
        if c.amount.value is not None and Decimal(c.amount.value) < 0: raise ValueError('negative cost')
        if c.amount.value is None: missing.append('/costs/' + c.cost_id)
    if any(c.cost_type not in ('sourcing','transfer','replenishment','donor_opportunity') for c in option.sourcing_costs):
        raise ValueError('invalid sourcing cost type')
    if any(c.cost_type not in ('recovery','other_incremental') for c in option.incremental_disruption_costs):
        raise ValueError('invalid disruption cost type')
    if not benchmark.external_applicability_acknowledged: missing.append('/benchmark/external_applicability_acknowledged')
    if benchmark.idr_per_published_currency_unit is None: missing.append('/benchmark/idr_per_published_currency_unit')
    if not benchmark.conversion_assumption_acknowledged: missing.append('/benchmark/conversion_assumption_acknowledged')
    if option.donor_cost_status.status not in ('included','not_applicable','explicitly_excluded'):
        missing.append('/donor_cost_status')
    if option.donor_cost_status.status == 'included' and not any(
        c.cost_type in ('donor_opportunity', 'replenishment') for c in option.sourcing_costs
    ):
        missing.append('/donor_cost_status/included_cost')
    published_loss = Decimal(benchmark.rate_per_hour) * hours
    def wire(value): return format(value.normalize(), 'f')
    def total(items): return sum((Decimal(c.amount.value or '0') for c in items), Decimal('0'))
    def rounded(value): return str(value.quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN))
    sourcing, recovery = total(option.sourcing_costs), total(option.incremental_disruption_costs)
    result = dict(option_id=option.option_id,mode=benchmark.mode,status='incomplete' if missing else 'complete_with_exclusions',
        missing_inputs=missing,flags=['external_oem_benchmark','currency_iso_unknown','currency_mapping_is_simulation','not_contribution_margin'],
        exclusions=['Not an observed cost of the demo factory; production-loss accounting basis and price year unpublished.'],
        source_case_id=benchmark.case_id,source_url=benchmark.source_url,source_currency_iso=None,
        published_rate_per_hour=benchmark.rate_per_hour,published_unit_production_loss=wire(published_loss),
        effective_scheduled_impacted_hours=wire(hours),elapsed_restore_hours=wire(elapsed),restore_at=restored,
        sourcing_total=rounded(sourcing),sourcing_total_unrounded=str(sourcing),
        incremental_disruption_total=rounded(recovery),incremental_disruption_total_unrounded=str(recovery),
        estimated_production_loss=None,unrecoverable_lost_contribution=None,
        future_relevant_option_total=None,future_relevant_option_total_unrounded=None,
        benchmark=benchmark.model_dump())
    if partial_horizon: result['flags'].append('partial_horizon_not_full_recovery')
    if option.donor_cost_status.status == 'explicitly_excluded': result['exclusions'].append('Donor opportunity cost explicitly excluded')
    if not missing:
        loss = published_loss * Decimal(benchmark.idr_per_published_currency_unit)
        result.update(estimated_production_loss=rounded(loss),estimated_production_loss_unrounded=str(loss),
            estimated_economic_disruption=rounded(loss+recovery),future_relevant_option_total=rounded(sourcing+recovery+loss),
            future_relevant_option_total_unrounded=wire(sourcing+recovery+loss))
    return result
