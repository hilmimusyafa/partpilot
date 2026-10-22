"""Evidence-based bearing matching within a bounded, warehouse-scoped catalog."""

import re
import uuid
from typing import Any, Dict, List, Optional
from backend.wo.models import Evidence, Fact, Question

BRAND_PATTERN = re.compile(r"\b(NTN|NSK|SKF|KOYO|FAG|NACHI)\b", re.I)
BASE_PATTERN = re.compile(r"\b(6\d{3})(?=\b|LLU|LLB|LLF|LLH|ZZ|2RS|DDU|OPEN)", re.I)
SUFFIX_PATTERN = re.compile(r"(?<![A-Z])(LLU|ZZ|2RS|LLB|LLF|LLH|DDU|OPEN)\b", re.I)
UNSUPPORTED_DIMENSION_UNIT = r"(?:(?:cm|m|in|inch|inches|inci|centimet(?:er|re)s?|met(?:er|re)s?)\b|[\"″])"
UNSUPPORTED_DIMENSION_PATTERN = re.compile(
    rf"(?:\d+(?:[.,]\d+)?\s*[xX*×]\s*\d+(?:[.,]\d+)?\s*[xX*×]\s*\d+(?:[.,]\d+)?|"
    rf"(?:diameter\s+(?:dalam|luar)|lubang|lebar|tebal)\s*[:=]?\s*\d+(?:[.,]\d+)?)\s*\(?\s*{UNSUPPORTED_DIMENSION_UNIT}", re.I)
DIMENSION_PATTERN = re.compile(
    r"(?<![\w.,+\-])(\d{1,3})\s*[xX*×]\s*(\d{1,3})\s*[xX*×]\s*(\d{1,3})"
    rf"(?![\w]|[.,]\d)(?!\s*\(?\s*{UNSUPPORTED_DIMENSION_UNIT})", re.I)
NAMED_DIMENSION_PATTERN = re.compile(
    r"\b(?:diameter\s+dalam|lubang)\s*[:=]?\s*(\d{1,3})\s*mm\s*[,;]?\s*"
    r"diameter\s+luar\s*[:=]?\s*(\d{1,3})\s*mm\s*[,;]?\s*"
    r"(?:lebar|tebal)\s*[:=]?\s*(\d{1,3})\s*mm\b", re.I)
ITEM_CODE_PATTERN = re.compile(r"\b([A-Z0-9]+(?:-[A-Z0-9]+)+)\b")
_SIDES = r"(?:di\s+)?(?:dua|kedua)\s+sisi"
SEAL_PATTERNS = [
    (re.compile(rf"\b(?:karet\s+rapat\s+{_SIDES}|contact(?: seals?)? both sides)\b", re.I), "contact_both_sides"),
    (re.compile(rf"\b(?:plat(?:\s+logam)?\s+{_SIDES}|metal shields? both sides)\b", re.I), "metal_shield_both_sides"),
    (re.compile(rf"\b(?:karet\s+nonkontak\s+{_SIDES}|noncontact(?: seals?)? both sides)\b", re.I), "noncontact_both_sides"),
    (re.compile(rf"\b(?:penutup\s+)?karet\s+{_SIDES}\b", re.I), "rubber_both_sides"),
]


def normalize_dimensions(text: str) -> Optional[str]:
    for pattern in (DIMENSION_PATTERN, NAMED_DIMENSION_PATTERN):
        raw = text.strip()
        if pattern is DIMENSION_PATTERN:
            raw = re.sub(r'\s+mm$', '', raw, flags=re.I)
        match = pattern.fullmatch(raw)
        if match and all(int(v) > 0 for v in match.groups()):
            return 'x'.join(str(int(v)) for v in match.groups())
    return None


def normalize_seal_type(text: str) -> Optional[str]:
    return next((value for pattern, value in SEAL_PATTERNS if pattern.fullmatch(text.strip())), None)


def extract_facts_from_text(text: str, source_field: str = "description") -> List[Fact]:
    """Extract observations only, preserving exact evidence (never derive an MPN)."""
    facts = []

    def add(key, value, raw):
        facts.append(Fact(key=key, value=value, source=source_field,
                          evidence=[Evidence(source_field=source_field, raw_substring=raw, normalized_value=value)]))

    for key, pattern in [('brand', BRAND_PATTERN), ('base', BASE_PATTERN), ('suffix', SUFFIX_PATTERN), ('item_code', ITEM_CODE_PATTERN)]:
        for match in pattern.finditer(text or ''):
            add(key, match.group(1).upper(), match.group(1))
    for pattern in (DIMENSION_PATTERN, NAMED_DIMENSION_PATTERN):
        for match in pattern.finditer(text or ''):
            value = normalize_dimensions(match.group())
            if value:
                add('dimensions', value, match.group())
    for pattern, value in SEAL_PATTERNS:
        for match in pattern.finditer(text or ''):
            add('seal_type', value, match.group())
    return facts


def _physical_metadata(row):
    """Read attributes recorded on this row, never infer size-to-series mappings.

    Synthetic catalog descriptions are user-provided and manufacturer-unverified.
    """
    text = ' '.join(str(row.get(k) or '') for k in ('item_name', 'description'))
    facts = extract_facts_from_text(text)
    result = {}
    for key in ('dimensions', 'seal_type'):
        values = {f.value for f in facts if f.key == key}
        if len(values) == 1:
            result[key] = next(iter(values))
    return result


def match_candidates(
    candidates: List[Dict[str, Any]], facts: List[Fact], answers: Optional[List[Any]] = None,
    clarification_round: int = 0, truncated: bool = False,
    knowledge_status: str = 'available', input_text: str = '',
) -> Dict[str, Any]:
    from backend.wo.identity import candidate_identity, has_unsupported_modifier

    def outcome(state, matched=(), questions=(), reason=None):
        return dict(state=state, identified_candidate=matched[0] if state == 'identified' else None,
                    matched_candidates=list(matched), questions=list(questions), conflicts=[], reason=reason)

    if knowledge_status == 'knowledge_unavailable':
        return outcome('knowledge_unavailable', reason='knowledge_unavailable')
    if UNSUPPORTED_DIMENSION_PATTERN.search(input_text):
        return outcome('needs_review', reason='unsupported_dimension_unit')
    # Descriptions can request clearance/precision without supplying an MPN.
    if has_unsupported_modifier(input_text) or re.search(r'\b(?:C[1-5]|CN|P[0-9])\b', input_text, re.I):
        return outcome('needs_review', reason='unsupported_designation_modifier')

    keys = ('brand', 'base', 'suffix', 'item_code', 'item_name', 'dimensions', 'seal_type')
    values = {k: {f.value.upper() if k in ('brand', 'base', 'suffix') else f.value
                  for f in facts if f.key == k} for k in keys}
    if any(len(v) > 1 for v in values.values()):
        result = outcome('needs_review', reason='contradictory_identity_evidence')
        result['conflicts'] = [dict(key=k, values=sorted(v), message=f'Conflicting {k} observations')
                               for k, v in values.items() if len(v) > 1]
        return result
    known = {k: next(iter(v)) for k, v in values.items() if v}
    exact = bool(known.get('item_code') or known.get('item_name') or all(k in known for k in ('brand', 'base', 'suffix')))
    # Noncontact cannot distinguish LLB/LLF, even with one catalog result.
    precise_seal = known.get('seal_type') in ('contact_both_sides', 'metal_shield_both_sides')
    physical = bool(known.get('brand') and known.get('dimensions') and (precise_seal or known.get('suffix')))
    matched, incomplete = [], False
    for row in candidates:
        identity = candidate_identity(row)
        if any(known.get(k) and row.get(k, '') != known[k] for k in ('item_code', 'item_name')):
            continue
        # Unknown identity is a blocker, not evidence a row does not match.
        if identity and any(k in known and known[k] != identity[k] for k in ('brand', 'base', 'suffix')):
            continue
        if not identity and known.get('brand') and row.get('brand') and row['brand'].upper() != known['brand']:
            continue
        attributes = _physical_metadata(row)
        mismatch = False
        missing_metadata = not identity
        for key in ('dimensions', 'seal_type'):
            if key not in known:
                continue
            if key not in attributes:
                missing_metadata = True
                continue
            if key == 'seal_type' and known[key] == 'rubber_both_sides':
                mismatch |= attributes[key] not in ('contact_both_sides', 'noncontact_both_sides', 'rubber_both_sides')
            else:
                mismatch |= attributes[key] != known[key]
        if mismatch:
            continue
        matched.append(row)
        incomplete |= missing_metadata

    if (exact or physical) and incomplete:
        return outcome('needs_review', matched, reason='catalog_physical_metadata_incomplete')
    if (exact or physical) and len(matched) == 1 and not truncated:
        return outcome('identified', matched, reason='exact_evidence_match' if exact else 'scoped_physical_evidence_match')
    if (exact or physical) and not matched and not truncated:
        return outcome('no_match', reason='no_catalog_match_for_criteria')
    if clarification_round >= 3:
        return outcome('needs_review', matched, reason='clarification_rounds_exhausted')
    missing = []
    if 'brand' not in known:
        missing.append('brand')
    if 'dimensions' not in known and ('base' not in known or precise_seal):
        missing.append('dimensions')
    if 'suffix' not in known and not precise_seal:
        missing.append('suffix' if known.get('seal_type') == 'noncontact_both_sides' else 'seal_type')
    prompts = {
        'brand': 'Apa merek yang terlihat pada bearing atau kemasannya? Jika tidak terbaca, sampaikan tidak terbaca.',
        'dimensions': 'Berapa diameter dalam, diameter luar, dan lebar bearing dalam mm? Contoh: 10 x 30 x 9.',
        'seal_type': 'Seperti apa penutup di kedua sisi: plat logam, karet rapat/kontak, atau karet nonkontak? Jika belum pasti, sampaikan ciri yang terlihat.',
        'suffix': 'Penutup nonkontak belum membedakan variannya. Adakah tulisan LLB atau LLF pada bearing/kemasan? Jika tidak terbaca, perlu pemeriksaan petugas.',
    }
    questions = [Question(id=f'q_{key}_{uuid.uuid4().hex[:8]}', key=key, prompt=prompts[key]) for key in missing[:3]]
    if not questions:
        return outcome('needs_review', matched[:100], reason='catalog_truncated' if truncated else 'catalog_identity_ambiguous')
    return outcome('awaiting_clarification', matched[:100], questions, 'identity_incomplete_or_ambiguous')
