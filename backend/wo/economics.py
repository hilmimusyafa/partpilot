"""Deterministic Decimal economic disruption calculator for PartPilot Backend Bundle v3.
Normative specification: private/bundle-v3/AMENDMENT.md (ADR-005).
"""

from datetime import datetime
from decimal import Decimal, ROUND_HALF_EVEN, getcontext
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.wo.models import (
    DisruptionInput,
    DisruptionResult,
    EconomicOption,
    EconomicOptionResult,
    OperatingWindow,
    ProductionEconomics,
    RestoreSchedule,
    ScenarioInput,
    ScenarioResult,
)

# Precision 50 for all intermediate economic calculations
getcontext().prec = 50


def parse_rfc3339(ts_str: str) -> datetime:
    """Parse RFC3339 timestamp with UTC timezone."""
    # Normalize Z to +00:00
    if ts_str.endswith("Z"):
        ts_str = ts_str[:-1] + "+00:00"
    parsed = datetime.fromisoformat(ts_str)
    if parsed.utcoffset() is None: raise ValueError("timezone required")
    return parsed


def evaluate_schedule(
    schedule: RestoreSchedule,
) -> Tuple[Decimal, Decimal, str, Optional[List[str]]]:
    """Evaluate stage DAG and calendar operating windows intersection.
    Returns:
      (elapsed_restore_hours, effective_scheduled_impacted_hours, restore_at_iso, missing_inputs)
    """
    if schedule.scheduled_impacted_windows is None:
        return Decimal("0"), Decimal("0"), "", ["/schedule/scheduled_impacted_windows"]

    future_from_dt = parse_rfc3339(schedule.future_from)
    horizon_end_dt = parse_rfc3339(schedule.horizon_end)

    if horizon_end_dt <= future_from_dt:
        raise ValueError("horizon_end must be greater than future_from")

    stages = schedule.stages
    stage_map = {s.id: s for s in stages}

    if len(stage_map) != len(stages):raise ValueError('duplicate stage id')
    visited=set();visiting=set()
    def visit(key):
        if key in visiting:raise ValueError('cyclic stage dependency')
        if key in visited:return
        if key not in stage_map:raise ValueError('unknown stage dependency')
        visiting.add(key)
        for predecessor in stage_map[key].depends_on:visit(predecessor)
        visiting.remove(key);visited.add(key)
    for key in stage_map:visit(key)
    previous_end=None
    for w in sorted(schedule.scheduled_impacted_windows,key=lambda w:parse_rfc3339(w.start)):
        start,end=parse_rfc3339(w.start),parse_rfc3339(w.end)
        if end<=start or (previous_end is not None and start<previous_end):raise ValueError('overlapping or invalid operating windows')
        previous_end=end

    # Verify all 5 stage kinds exist
    stage_kinds = {s.kind for s in stages}
    required_kinds = {"procurement", "dispatch", "transport", "installation", "restart"}
    if not required_kinds.issubset(stage_kinds):
        raise ValueError(f"All 5 stage kinds required: missing {required_kinds - stage_kinds}")

    # Verify DAG ordering and intervals
    max_end_dt = future_from_dt
    for s in stages:
        s_start = parse_rfc3339(s.start)
        s_end = parse_rfc3339(s.end)
        if s_end < s_start:
            raise ValueError(f"Stage {s.id} end precedes start")
        if s_start < future_from_dt:
            raise ValueError(f"Stage {s.id} start precedes future_from")
        for pred_id in s.depends_on:
            if pred_id not in stage_map:
                raise ValueError(f"Predecessor stage {pred_id} not found")
            pred_end = parse_rfc3339(stage_map[pred_id].end)
            if s_start < pred_end:
                raise ValueError(f"Dependent stage {s.id} start precedes predecessor {pred_id} end")
        if s_end > max_end_dt:
            max_end_dt = s_end

    restore_at = max_end_dt
    elapsed_seconds = Decimal(str((restore_at - future_from_dt).total_seconds()))
    elapsed_restore_hours = elapsed_seconds / Decimal("3600")

    # Clip loss window to [future_from, min(restore_at, horizon_end)]
    loss_start = future_from_dt
    loss_end = min(restore_at, horizon_end_dt)

    # Intersect with scheduled operating windows
    total_impacted_seconds = Decimal("0")
    if loss_end > loss_start:
        for w in schedule.scheduled_impacted_windows:
            w_start = parse_rfc3339(w.start)
            w_end = parse_rfc3339(w.end)
            if w_end < w_start:
                raise ValueError("Operating window end precedes start")
            # Interval intersection
            inter_start = max(loss_start, w_start)
            inter_end = min(loss_end, w_end)
            if inter_end > inter_start:
                total_impacted_seconds += Decimal(str((inter_end - inter_start).total_seconds()))

    effective_scheduled_impacted_hours = total_impacted_seconds / Decimal("3600")
    return elapsed_restore_hours, effective_scheduled_impacted_hours, restore_at.isoformat(), None


def calculate_option_economics(
    production: ProductionEconomics,
    option: EconomicOption,
) -> EconomicOptionResult:
    """Calculate deterministic Decimal economics for single option."""
    # 1. Non-duplication assertions
    if not option.costs_nonduplicated:
        raise ValueError("Option requires costs_nonduplicated: true")

    all_costs = option.sourcing_costs + option.incremental_disruption_costs
    cost_ids = [c.cost_id for c in all_costs]
    evidence_refs = [c.evidence_ref for c in all_costs]

    if len(cost_ids) != len(set(cost_ids)):
        raise ValueError(f"Duplicate cost_id detected across option {option.option_id} costs")
    if len(evidence_refs) != len(set(evidence_refs)):
        raise ValueError(f"Duplicate evidence_ref detected across option {option.option_id} costs")

    for cost in all_costs:
        if cost.amount.unit != production.currency: raise ValueError("incomparable cost currency")
        if cost.amount.value is not None and Decimal(cost.amount.value)<0: raise ValueError("negative cost")

    # Cost types validation
    sourcing_allowed = {"sourcing", "transfer", "donor_opportunity", "replenishment"}
    for sc in option.sourcing_costs:
        if sc.cost_type not in sourcing_allowed:
            raise ValueError(f"Invalid sourcing cost_type '{sc.cost_type}'")

    disruption_allowed = {"recovery", "other_incremental"}
    for dc in option.incremental_disruption_costs:
        if dc.cost_type not in disruption_allowed:
            raise ValueError(f"Invalid incremental disruption cost_type '{dc.cost_type}'")

    missing_inputs: List[str] = []
    exclusions: List[str] = []
    flags: List[str] = []

    # Check for missing production economic inputs
    prod_fields = [
        ("normal_output_per_hour", production.normal_output_per_hour),
        ("disrupted_output_per_hour", production.disrupted_output_per_hour),
        ("recoverable_fraction", production.recoverable_fraction),
        ("net_selling_price_per_unit", production.net_selling_price_per_unit),
        ("avoidable_variable_cost_per_unit", production.avoidable_variable_cost_per_unit),
    ]
    for field_name, datum in prod_fields:
        if datum.value is None:
            missing_inputs.append(f"/production/{field_name}")

    # Check for missing cost amounts
    for sc in option.sourcing_costs:
        if sc.amount.value is None:
            missing_inputs.append(f"/options/{option.option_id}/sourcing_costs/{sc.cost_id}/amount")
    for dc in option.incremental_disruption_costs:
        if dc.amount.value is None:
            missing_inputs.append(f"/options/{option.option_id}/incremental_disruption_costs/{dc.cost_id}/amount")

    # Donor cost handling
    donor_status = option.donor_cost_status.status
    donor_entries = [c for c in option.sourcing_costs if c.cost_type in ("donor_opportunity", "replenishment")]
    if donor_status not in ("included", "not_applicable", "explicitly_excluded") or (donor_status == "included" and not donor_entries):
        missing_inputs.append(f"/options/{option.option_id}/donor_cost_status")
    if donor_status == "explicitly_excluded":
        exclusions.append(f"Donor costs explicitly excluded: {option.donor_cost_status.reason or 'unspecified'}")

    # Schedule evaluation
    try:
        elapsed_restore_h, impacted_h, restore_at_iso, sched_missing = evaluate_schedule(option.schedule)
        if sched_missing:
            missing_inputs.extend(sched_missing)
    except Exception as e:
        raise ValueError(f"Schedule evaluation error: {e}")

    scale = production.currency_scale
    round_exp = Decimal(f"1e-{scale}")

    # If any necessary inputs are missing, return incomplete status with retained raw inputs
    if missing_inputs:
        return EconomicOptionResult(
            option_id=option.option_id,
            status="incomplete",
            missing_inputs=missing_inputs,
            exclusions=exclusions,
            flags=flags,
            restore_at=restore_at_iso,
            elapsed_restore_hours=str(elapsed_restore_h) if elapsed_restore_h else None,
            effective_scheduled_impacted_hours=str(impacted_h) if impacted_h else None,
        )

    # All necessary inputs present: compute formulas
    normal_rate = Decimal(production.normal_output_per_hour.value or "0")
    disrupted_rate = Decimal(production.disrupted_output_per_hour.value or "0")
    rec_frac = Decimal(production.recoverable_fraction.value or "0")
    price = Decimal(production.net_selling_price_per_unit.value or "0")
    var_cost = Decimal(production.avoidable_variable_cost_per_unit.value or "0")

    lost_output = (normal_rate - disrupted_rate) * impacted_h
    unit_contribution = price - var_cost
    if unit_contribution < Decimal("0"):
        flags.append("negative_contribution_margin")

    unrec_lost_contrib = lost_output * (Decimal("1") - rec_frac) * unit_contribution

    # Sourcing total
    sourcing_total = sum((Decimal(sc.amount.value) for sc in option.sourcing_costs), Decimal("0"))
    # Incremental disruption total
    incremental_total = sum((Decimal(dc.amount.value) for dc in option.incremental_disruption_costs), Decimal("0"))

    estimated_disruption = unrec_lost_contrib + incremental_total
    future_relevant_total = sourcing_total + estimated_disruption

    # Status: complete vs complete_with_exclusions
    opt_status = "complete_with_exclusions" if exclusions else "complete"

    def fmt(d: Decimal) -> str:
        return str(d.quantize(round_exp, rounding=ROUND_HALF_EVEN))

    return EconomicOptionResult(
        option_id=option.option_id,
        status=opt_status,
        missing_inputs=[],
        exclusions=exclusions,
        flags=flags,
        contribution_margin=fmt(unit_contribution),
        contribution_margin_unrounded=str(unit_contribution),
        effective_scheduled_impacted_hours=str(impacted_h),
        lost_output=str(lost_output),
        unrecoverable_lost_contribution=fmt(unrec_lost_contrib),
        unrecoverable_lost_contribution_unrounded=str(unrec_lost_contrib),
        incremental_disruption_total=fmt(incremental_total),
        incremental_disruption_total_unrounded=str(incremental_total),
        sourcing_total=fmt(sourcing_total),
        sourcing_total_unrounded=str(sourcing_total),
        estimated_economic_disruption=fmt(estimated_disruption),
        estimated_economic_disruption_unrounded=str(estimated_disruption),
        future_relevant_option_total=fmt(future_relevant_total),
        future_relevant_option_total_unrounded=str(future_relevant_total),
        restore_at=restore_at_iso,
        elapsed_restore_hours=str(elapsed_restore_h),
    )


def calculate_scenario_economics(scenario: ScenarioInput) -> List[EconomicOptionResult]:
    """Calculate economics for one scenario."""
    return [calculate_option_economics(scenario.production, opt) for opt in scenario.options]


def evaluate_disruption(payload: DisruptionInput) -> DisruptionResult:
    """Evaluate economic disruption across base options and optional scenarios."""
    base_results = [calculate_option_economics(payload.production, opt) for opt in payload.options]

    scenarios_results: Optional[Dict[str, List[EconomicOptionResult]]] = None
    if payload.scenarios:
        scenarios_results = {}
        for sc_name, sc_input in payload.scenarios.items():
            # Incomparable scenario checks
            if sc_input.production.currency != payload.production.currency:
                raise ValueError(f"Incomparable scenario '{sc_name}': currency mismatch")
            if sc_input.production.output_unit != payload.production.output_unit:
                raise ValueError(f"Incomparable scenario '{sc_name}': output_unit mismatch")
            scenarios_results[sc_name] = calculate_scenario_economics(sc_input)

    return DisruptionResult(
        api_version="backend-bundle-v3",
        company_id=payload.company_id,
        context=payload.context,
        base_options=base_results,
        scenarios=scenarios_results,
    )
