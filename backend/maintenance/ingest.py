"""Import reviewed structured extracts only, never stock fixtures or invented events."""
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def _read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def _sources(path):
    return {row['source_id']: row for row in _read(path)}


def _record(ident, kind, title, facts, source, locator=None, default_retrieval=True):
    url = source['url']
    sha = source['sha256']
    if urlparse(url).scheme != 'https' or len(sha) != 64 or any(c not in '0123456789abcdef' for c in sha.lower()):
        raise ValueError('Evidence requires an HTTPS source and captured SHA-256')
    ref = {
        'source_id': source['source_id'], 'url': url, 'locator': locator or source['locator'],
        'sha256': sha,
        'retrieved_at': source.get('fetched_at_utc') or source.get('retrieved_utc'),
    }
    record = {'id': ident, 'kind': kind, 'title': title, 'facts': facts,
              'source_refs': [ref], 'default_retrieval': default_retrieval,
              'is_local_asset_history': False}
    record['content_sha256'] = digest(record)
    return record


def load_evidence_pack(history_dir, economics_dir):
    history_dir, economics_dir = Path(history_dir), Path(economics_dir)
    sources = _sources(history_dir / 'source_manifest.json')
    history = _read(history_dir / 'data/published_history.json')
    if history['is_partpilot_user_asset_history'] or history['is_customer_cmms_export']:
        raise ValueError('Only external published case evidence belongs in this pack')
    result = [_record('history:' + history['case_id'], 'published_case', 'NSK food production conveyor',
                      history, sources[history['source_id']])]
    catalog = _read(history_dir / 'data/catalog_parts.json')
    for key, role in [('selected_demo_request', 'proposed_demo_exact'), ('alternative_candidate', 'engineering_candidate')]:
        part = catalog[key]
        facts = {
            'part': part, 'role': role, 'historical_case_BOM_claim': False,
            'shared_catalog_interface_mm': catalog['shared_catalog_interface_mm'],
            'technical_approval_missing': catalog['technical_approval_missing'],
            'negative_controls': catalog['negative_controls'],
            'alternative_insert_operating_limits': catalog['alternative_insert_operating_limits'] if role == 'engineering_candidate' else None,
            'food_grade_evidence': catalog['alternative_food_grade_evidence'] if role == 'engineering_candidate' else None,
        }
        result.append(_record('catalog:' + part['sku'], 'catalog_part', 'RHP ' + part['sku'], facts,
                              sources[catalog['source_id']], 'Printed catalog pages ' + ', '.join(map(str, part['catalog_pages']))))
    guidance = _read(history_dir / 'data/troubleshooting_guidance.json')
    result.append(_record('troubleshooting:' + guidance['damage_type'], 'troubleshooting', 'NSK rust and corrosion guidance',
                          guidance, sources[guidance['source_id']], guidance['locator']))
    cost_sources = _sources(economics_dir / 'source_manifest.json')
    for case in _read(economics_dir / 'published_cost_cases.json'):
        case_id = case.get('case_id') or case['record_id']
        result.append(_record('economics:' + case_id, 'economic_case', case['application'], case,
                              cost_sources[case_id], default_retrieval=case_id in {'NSK-SS-E-2003', 'NSK-SS-E-2054'}))
    return result
