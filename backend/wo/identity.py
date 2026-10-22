"""Exact manufacturer label parsing; local names/dimensions never invent identity."""
import re

LEGACY_BRANDS = {'NTN', 'NSK', 'SKF', 'KOYO', 'FAG', 'NACHI'}
LEGACY_SUFFIXES = {'LLU', 'LLB', 'LLF', 'LLH', 'ZZ', '2RS', 'DDU', 'OPEN'}
BRANDS = re.compile(r'(?<![A-Z0-9])(NTN|NSK|SKF|KOYO|FAG|NACHI|RHP)(?![A-Z0-9])', re.I)
MPN = re.compile(r'(?<![A-Z0-9])(6\d{3})(?:\s*/\s*|\s*)(LLU|LLB|LLF|LLH|ZZ|2RS|DDU|OPEN)(?![A-Z0-9])', re.I)
LABEL_FRAGMENT = re.compile(r'(?<![A-Z0-9])(?:6\d{3}(?:\s*/\s*|\s*))?(LLU|LLB|LLF|LLH|ZZ|2RS|DDU|OPEN)(?![A-Z0-9])', re.I)
COMPLETE_SUFFIXES = {'PSF20CR': 'CR', 'PSF20/LP99': '/LP99'}
COMPLETE_LABEL = re.compile(r'(?<![A-Z0-9/\-])(PSF20CR|PSF20/LP99)(?![A-Z0-9/\-])', re.I)
IDENTITY_KEYS = ('brand', 'base', 'suffix', 'manufacturer', 'full_designation', 'unit_scope')


def complete_identity(designation):
    """Closed, catalog-backed unit identities; no dimensions or brand aliases."""
    if designation not in COMPLETE_SUFFIXES:
        return None
    return dict(brand='RHP', base='PSF20', suffix=COMPLETE_SUFFIXES[designation],
                manufacturer='RHP', full_designation=designation, unit_scope='complete_housed_unit')


def canonical_identity(identity):
    """Validate an identity without dropping scope, modifiers, or full designation."""
    if not isinstance(identity, dict):
        return None
    provided = {k: identity[k] for k in IDENTITY_KEYS if k in identity}
    expected = complete_identity(provided.get('full_designation'))
    if expected:
        return expected if provided == expected else None
    if (set(provided) == {'brand', 'base', 'suffix'} and
            provided['brand'] in LEGACY_BRANDS and
            re.fullmatch(r'6\d{3}', str(provided['base'])) and
            provided['suffix'] in LEGACY_SUFFIXES):
        return provided
    return None

def has_unsupported_modifier(text):
    # The demo understands the base and closure only. Never discard additional
    # clearance/precision/design modifiers such as /C3, -C3 or space C3.
    modifier = r'(?:\s*[-/]\s*[A-Z0-9]|\s+(?:C\d|CN\b|P\d|[A-Z]\d+[A-Z0-9]*\b))'
    for match in re.finditer(r'\bPSF\d+[A-Z0-9/\-]*', text, re.I):
        if match.group().upper() not in COMPLETE_SUFFIXES or re.match(modifier, text[match.end():], re.I):
            return True
    return any(re.match(modifier, text[m.end():],re.I) for m in LABEL_FRAGMENT.finditer(text))

def candidate_identity(candidate):
    text = ' '.join(str(candidate.get(k) or '') for k in ('item_name','description'))
    if has_unsupported_modifier(text):return None
    brands = {m.group(1).upper() for m in BRANDS.finditer(text)}
    recorded = {k: candidate[k] for k in IDENTITY_KEYS if k in candidate}
    if not recorded.get('brand'):
        recorded.pop('brand', None)
    if candidate.get('brand'):
        brands.add(candidate['brand'].strip().upper())
        recorded['brand'] = candidate['brand'].strip().upper()
    complete_labels = {m.group(1).upper() for m in COMPLETE_LABEL.finditer(text)}
    labels = {(m.group(1),m.group(2).upper()) for m in MPN.finditer(text)}
    if complete_labels:
        if brands != {'RHP'} or len(complete_labels) != 1 or labels:
            return None
        identity = complete_identity(next(iter(complete_labels)))
        if any(value != identity.get(k) for k, value in recorded.items()):
            return None
        return identity
    if len(brands)!=1 or len(labels)!=1:
        return None
    base,suffix=next(iter(labels))
    identity = {'brand':next(iter(brands)),'base':base,'suffix':suffix}
    if any(value != identity.get(k) for k, value in recorded.items()):
        return None
    return canonical_identity(identity)

def same_identity(source, target):
    source, target = canonical_identity(source), canonical_identity(target)
    return source is not None and target is not None and source == target
