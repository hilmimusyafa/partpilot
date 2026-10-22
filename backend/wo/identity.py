"""Exact manufacturer label parsing; local names/dimensions never invent identity."""
import re

BRANDS = re.compile(r'(?<![A-Z0-9])(NTN|NSK|SKF|KOYO|FAG|NACHI)(?![A-Z0-9])', re.I)
MPN = re.compile(r'(?<![A-Z0-9])(6\d{3})(?:\s*/\s*|\s*)(LLU|LLB|LLF|LLH|ZZ|2RS|DDU|OPEN)(?![A-Z0-9])', re.I)
LABEL_FRAGMENT = re.compile(r'(?<![A-Z0-9])(?:6\d{3}(?:\s*/\s*|\s*))?(LLU|LLB|LLF|LLH|ZZ|2RS|DDU|OPEN)(?![A-Z0-9])', re.I)

def has_unsupported_modifier(text):
    # The demo understands the base and closure only. Never discard additional
    # clearance/precision/design modifiers such as /C3, -C3 or space C3.
    return any(re.match(r'(?:\s*[-/]\s*[A-Z0-9]|\s+(?:C\d|CN\b|P\d|[A-Z]\d+[A-Z0-9]*\b))',
                        text[m.end():],re.I) for m in LABEL_FRAGMENT.finditer(text))

def candidate_identity(candidate):
    text = ' '.join(str(candidate.get(k) or '') for k in ('item_name','description'))
    if has_unsupported_modifier(text):return None
    brands = {m.group(1).upper() for m in BRANDS.finditer(text)}
    if candidate.get('brand'):
        brands.add(candidate['brand'].strip().upper())
    labels = {(m.group(1),m.group(2).upper()) for m in MPN.finditer(text)}
    if len(brands)!=1 or len(labels)!=1:
        return None
    base,suffix=next(iter(labels))
    return {'brand':next(iter(brands)),'base':base,'suffix':suffix}

def same_identity(source, target):
    return all(source.get(k) and source[k]==target.get(k) for k in ('brand','base','suffix'))
