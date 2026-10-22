"""Deterministic candidate matching and clarification for PartPilot Backend Bundle v3."""

import re
import uuid
from typing import Any, Dict, List, Optional, Tuple
from backend.wo.models import Candidate, Evidence, Fact, Question


# Known brand regex
BRAND_PATTERN = re.compile(r"\b(NTN|NSK|SKF|KOYO|FAG|NACHI)\b", re.IGNORECASE)
# Bearing series/base code (e.g. 6200, 6000, 6300, 6800, 6900)
BASE_PATTERN = re.compile(r"\b(6[02389]\d{2})\b")
# Bearing suffix (e.g. LLU, ZZ, 2RS, LLB, LLF, DDU)
SUFFIX_PATTERN = re.compile(r"\b(LLU|ZZ|2RS|LLB|LLF|DDU|OPEN)\b", re.IGNORECASE)
# Dimensions pattern (d x D x B in mm)
DIMENSION_PATTERN = re.compile(r"\b(\d{1,3})\s*[xX*]\s*(\d{1,3})\s*[xX*]\s*(\d{1,3})\b")
# Local item code pattern
ITEM_CODE_PATTERN = re.compile(r"\b([A-Z0-9]+(?:-[A-Z0-9]+)+)\b")


def extract_facts_from_text(text: str, source_field: str = "description") -> List[Fact]:
    """Extract bounded, verifiable facts from text with source substring evidence."""
    if not text:
        return []

    facts: List[Fact] = []

    # 1. Brand
    for match in BRAND_PATTERN.finditer(text):
        val = match.group(1).upper()
        facts.append(Fact(
            key="brand",
            value=val,
            source=source_field,
            evidence=[Evidence(source_field=source_field, raw_substring=match.group(0), normalized_value=val)]
        ))

    # 2. Base / Series
    for match in BASE_PATTERN.finditer(text):
        val = match.group(1)
        facts.append(Fact(
            key="base",
            value=val,
            source=source_field,
            evidence=[Evidence(source_field=source_field, raw_substring=match.group(0), normalized_value=val)]
        ))

    # 3. Suffix
    for match in SUFFIX_PATTERN.finditer(text):
        val = match.group(1).upper()
        facts.append(Fact(
            key="suffix",
            value=val,
            source=source_field,
            evidence=[Evidence(source_field=source_field, raw_substring=match.group(0), normalized_value=val)]
        ))

    # 4. Dimensions
    for match in DIMENSION_PATTERN.finditer(text):
        d, D, B = match.group(1), match.group(2), match.group(3)
        dim_val = f"{d}x{D}x{B}"
        facts.append(Fact(
            key="dimensions",
            value=dim_val,
            source=source_field,
            evidence=[Evidence(source_field=source_field, raw_substring=match.group(0), normalized_value=dim_val)]
        ))

    # 5. Local item codes
    for match in ITEM_CODE_PATTERN.finditer(text):
        val = match.group(1)
        # Exclude pure dimension or noise
        if "-" in val:
            facts.append(Fact(
                key="item_code",
                value=val,
                source=source_field,
                evidence=[Evidence(source_field=source_field, raw_substring=match.group(0), normalized_value=val)]
            ))

    # 6. Indonesian local semantics from WH02
    text_upper = text.upper()
    if "KARET RAPAT DUA SISI" in text_upper:
        facts.append(Fact(
            key="seal_type",
            value="contact_both_sides",
            source=source_field,
            evidence=[Evidence(source_field=source_field, raw_substring="KARET RAPAT DUA SISI", normalized_value="LLU")]
        ))
    elif "PLAT DUA SISI" in text_upper:
        facts.append(Fact(
            key="seal_type",
            value="metal_shield_both_sides",
            source=source_field,
            evidence=[Evidence(source_field=source_field, raw_substring="PLAT DUA SISI", normalized_value="ZZ")]
        ))
    elif "KARET NONKONTAK DUA SISI" in text_upper:
        # Ambiguous between LLB and LLF
        facts.append(Fact(
            key="seal_type",
            value="noncontact_both_sides",
            source=source_field,
            evidence=[Evidence(source_field=source_field, raw_substring="KARET NONKONTAK DUA SISI", normalized_value="LLB_OR_LLF")]
        ))

    return facts


def match_candidates(
    candidates: List[Dict[str, Any]],
    facts: List[Fact],
    answers: Optional[List[Any]] = None,
    clarification_round: int = 0,
    truncated: bool = False,
    knowledge_status: str = "available",
    input_text: str = "",
) -> Dict[str, Any]:
    """Deterministic candidate matching algorithm according to settled decisions 6, 7, 8.
    Returns:
      {
        'state': 'identified' | 'no_match' | 'awaiting_clarification' | 'needs_review' | 'knowledge_unavailable',
        'identified_candidate': Optional[Dict[str, Any]],
        'matched_candidates': List[Dict[str, Any]],
        'questions': List[Question],
        'conflicts': List[str],
        'reason': Optional[str]
      }
    """
    if knowledge_status == "knowledge_unavailable":
        return {
            "state": "knowledge_unavailable",
            "identified_candidate": None,
            "matched_candidates": [],
            "questions": [],
            "conflicts": [],
            "reason": "knowledge_unavailable"
        }

    from backend.wo.identity import candidate_identity, has_unsupported_modifier
    values = {k: {str(f.value) if k in ('item_code','item_name') else str(f.value).upper() for f in facts if f.key == k}
              for k in ('brand','base','suffix','item_code','item_name')}
    def outcome(state, matched=(), questions=(), reason=None):
        return {'state':state,'identified_candidate':matched[0] if state=='identified' else None,
                'matched_candidates':list(matched),'questions':list(questions),'conflicts':[], 'reason':reason}
    if has_unsupported_modifier(input_text):
        return outcome('needs_review',reason='unsupported_designation_modifier')
    if any(len(v)>1 for v in values.values()):
        result=outcome('needs_review',reason='contradictory_identity_evidence')
        result['conflicts']=[{'key':k,'values':sorted(v),'message':f'Conflicting {k} observations'}
                             for k,v in values.items() if len(v)>1]
        return result
    known={k:next(iter(v)) for k,v in values.items() if v}
    exact=bool(known.get('item_code') or known.get('item_name') or all(k in known for k in ('brand','base','suffix')))
    matched=[]
    for row in candidates:
        identity=candidate_identity(row)
        if known.get('item_code') and row.get('item_code','')!=known['item_code']:continue
        if known.get('item_name') and row.get('item_name','')!=known['item_name']:continue
        if any(k in known and (not identity or known[k]!=identity[k]) for k in ('brand','base','suffix')):continue
        matched.append(row)
    if exact and len(matched)==1 and not truncated:
        return outcome('identified',matched,reason='exact_evidence_match')
    if exact and not matched and not truncated:
        return outcome('no_match',reason='no_catalog_match_for_criteria')
    if clarification_round>=3:
        return outcome('needs_review',matched,reason='clarification_rounds_exhausted')
    missing=[k for k in ('brand','base','suffix') if k not in known]
    prompts={'brand':'Apa merek pada label bearing?', 'base':'Apa kode seri pada label bearing?', 'suffix':'Apa suffix lengkap pada label bearing (misalnya LLU, ZZ, LLB, LLF)?'}
    questions=[Question(id=f'q_{k}_{uuid.uuid4().hex[:8]}',key=k,prompt=prompts[k]) for k in missing[:3]]
    if not questions:
        questions=[Question(id=f'q_code_{uuid.uuid4().hex[:8]}',key='item_code',prompt='Sebutkan kode barang exact untuk membedakan kandidat.')]
    return outcome('awaiting_clarification',matched[:100],questions,'identity_incomplete_or_ambiguous')
