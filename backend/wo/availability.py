"""Read-only cross-warehouse availability evaluation for PartPilot Backend Bundle v3.
Normative specification: private/bundle-v3/AMENDMENT.md (ADR-004).
"""

from datetime import datetime, timezone
from decimal import Decimal
import uuid
from typing import Any, Dict, List, Optional, Tuple

from backend.wo.knowledge import load_scoped_note
from backend.wo.models import AvailabilityResult, AvailabilityScope, Session
from backend.wo.repository import get_db_connection, get_scoped_candidates, list_warehouses
from backend.wo.identity import candidate_identity, same_identity, canonical_identity


def match_cross_warehouse_identity(
    source_identity: Dict[str, Any],
    target_candidate: Dict[str, Any],
    target_note: Dict[str, Any],
) -> Tuple[bool, Optional[str]]:
    """Match cross-warehouse identity strictly:
    - Exact canonical identity required, including complete unit designation/scope.
    - Local item_code in source does NOT prove MPN in target.
    - Suffixes (LLU, ZZ, LLB, LLF) must match exactly; generic noncontact insufficient.
    - Returns (is_match, reason).
    """
    if canonical_identity(source_identity) is None:
        return False, 'insufficient_source_identity_evidence'
    target = candidate_identity(target_candidate)
    if target is None or not same_identity(source_identity, target):
        return False, 'identity_mismatch'
    return True, None


def evaluate_scope(
    warehouse_id: str,
    requested_qty: Decimal,
    source_identity: Dict[str, Any],
    category: str = "Bearing",
    company_id: str = "SYN-COMPANY-01",
) -> AvailabilityScope:
    """Evaluate single warehouse scope for availability."""
    identity = canonical_identity(source_identity)
    if identity and identity.get('unit_scope') == 'complete_housed_unit':
        from backend.wo.food_catalog import load_food_catalog_identity
        with get_db_connection() as conn:
            note_info = load_food_catalog_identity(conn, identity, company_id, warehouse_id, category)
    else:
        note_info = load_scoped_note(warehouse_id, category)
    if note_info.get("status") == "knowledge_unavailable":
        return AvailabilityScope(
            warehouse_id=warehouse_id,
            status="knowledge_unavailable",
            scoped_reason=note_info.get("reason"),
            knowledge_refs=[note_info],
        )

    if canonical_identity(source_identity) is None:
        return AvailabilityScope(warehouse_id=warehouse_id,status='identity_insufficient',knowledge_refs=[note_info])

    candidates, truncated = get_scoped_candidates(company_id, warehouse_id, category)

    matching_candidates: List[Dict[str, Any]] = []
    for cand in candidates:
        is_match, _ = match_cross_warehouse_identity(source_identity, cand, note_info)
        if is_match:
            matching_candidates.append(cand)

    if truncated:
        return AvailabilityScope(
            warehouse_id=warehouse_id,
            status="ambiguous",
            scoped_reason="truncated_catalog_ambiguity",
            knowledge_refs=[note_info],
        )

    if len(matching_candidates) > 1:
        return AvailabilityScope(
            warehouse_id=warehouse_id,
            status="ambiguous",
            scoped_reason="multiple_identical_candidates_cannot_sum",
            knowledge_refs=[note_info],
        )

    if len(matching_candidates) == 0:
        return AvailabilityScope(
            warehouse_id=warehouse_id,
            status="not_found",
            scoped_reason="definite_negative_known_note",
            knowledge_refs=[note_info],
        )

    cand = matching_candidates[0]
    if cand.get("stock_uom") != "Nos":
        return AvailabilityScope(warehouse_id=warehouse_id,status="identity_insufficient",
                                 scoped_reason="unit_mismatch_or_unknown",knowledge_refs=[note_info])
    if cand.get("actual_qty") is None or cand.get("reserved_qty") is None:
        return AvailabilityScope(warehouse_id=warehouse_id,status="identity_insufficient",
                                 scoped_reason="unknown_quantity",knowledge_refs=[note_info])
    actual = Decimal(cand.get("actual_qty") or "0")
    reserved = Decimal(cand.get("reserved_qty") or "0")
    available = max(actual - reserved, Decimal("0"))
    shortage = max(requested_qty - available, Decimal("0"))

    status = "sufficient" if available >= requested_qty else "insufficient"

    return AvailabilityScope(
        warehouse_id=warehouse_id,
        status=status,
        item_code=cand.get("item_code"),
        actual_qty=str(actual),
        reserved_qty=str(reserved),
        available_qty=str(available),
        shortage_qty=str(shortage),
        quantity_unit="Nos",
        evidence=[{k:cand.get(k) for k in ("item_code","item_name","brand","description","stock_uom","item_group")}],
        knowledge_refs=[note_info],
    )


def evaluate_availability(session: Session) -> AvailabilityResult:
    """Execute complete read-only availability evaluation across origin and alternatives."""
    snapshot_id = str(uuid.uuid4())
    as_of = datetime.now(timezone.utc).isoformat()
    company_id = session.company_id
    category = "Bearing"
    requested_qty_dec = Decimal(session.quantity or "1")

    # Extract source identity from session result
    result = session.result or {}
    identified_cand = result.get("identified_candidate") or {}
    cand_name = identified_cand.get("item_name", "") or session.description or ""

    source_identity = candidate_identity(identified_cand) or {}
    source_identity['item_code'] = identified_cand.get('item_code')

    origin_wh = session.warehouse_id or ""
    origin_scope = evaluate_scope(origin_wh, requested_qty_dec, source_identity, category, company_id)

    # Origin-first shortcut: if origin sufficient, return fulfilled_source immediately with alternatives=[]
    if origin_scope.status == "sufficient":
        return AvailabilityResult(
            api_version="backend-bundle-v3",
            session_id=session.id,
            session_version=session.version,
            snapshot_id=snapshot_id,
            as_of=as_of,
            company_id=company_id,
            category=category,
            identity_evidence=[{"source_field": "item_name", "raw_substring": cand_name}],
            requested_qty=str(requested_qty_dec),
            quantity_unit="Nos",
            status="fulfilled_source",
            origin=origin_scope,
            alternatives=[],
            complete=True,
            truncated=False,
            reservation=False,
        )

    # Origin is insufficient / absent: enumerate same-company active leaf warehouses
    wh_list, next_cursor = list_warehouses(company_id, limit=100)
    other_whs = [w.id for w in wh_list if w.id != origin_wh]

    truncated = bool(next_cursor)
    eval_whs = other_whs[:100]

    alternatives: List[AvailabilityScope] = []
    all_conclusive = not truncated
    for wh_id in eval_whs:
        scope_res = evaluate_scope(wh_id, requested_qty_dec, source_identity, category, company_id)
        alternatives.append(scope_res)
        if scope_res.status in ("knowledge_unavailable", "identity_insufficient", "ambiguous"):
            all_conclusive = False

    return AvailabilityResult(
        api_version="backend-bundle-v3",
        session_id=session.id,
        session_version=session.version,
        snapshot_id=snapshot_id,
        as_of=as_of,
        company_id=company_id,
        category=category,
        identity_evidence=[{"source_field": "item_name", "raw_substring": cand_name}],
        requested_qty=str(requested_qty_dec),
        quantity_unit="Nos",
        status="alternatives_evaluated",
        origin=origin_scope,
        alternatives=alternatives,
        complete=all_conclusive,
        truncated=truncated,
        reservation=False,
    )
