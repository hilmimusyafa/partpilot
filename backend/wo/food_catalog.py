"""Shared, scoped OEM evidence boundary for known RHP complete-unit identities."""
import json
import re
from urllib.parse import urlparse

import psycopg
from psycopg.rows import dict_row

from backend.maintenance.ingest import digest
from backend.wo.identity import canonical_identity
from backend.wo.knowledge import ALLOWLISTED_SCOPES


def load_food_catalog_identity(conn, identity, company_id, warehouse_id, category='Bearing'):
    """Read the selected immutable OEM extract; never fall back to AC naming notes."""
    unavailable = dict(status='knowledge_unavailable', reason='food_catalog_evidence_missing',
                       path='pp.maintenance_evidence', sha256='', source_status='UNAVAILABLE',
                       snapshot_version='', content_snapshot=None)
    if company_id != 'SYN-COMPANY-01' or category != 'Bearing' or (warehouse_id, category) not in ALLOWLISTED_SCOPES:
        return {**unavailable, 'reason': 'food_catalog_scope_unavailable'}
    identity = canonical_identity(identity)
    if not identity or identity.get('unit_scope') != 'complete_housed_unit':
        return {**unavailable, 'reason': 'food_catalog_identity_unsupported'}
    try:
        with conn.transaction(), conn.cursor(row_factory=dict_row) as cur:
            cur.execute('SET LOCAL statement_timeout = 2000')
            cur.execute('SELECT 1 FROM erp.warehouse WHERE name=%s AND company=%s AND NOT disabled AND NOT is_group',
                        (warehouse_id, company_id))
            if not cur.fetchone():
                return {**unavailable, 'reason': 'food_catalog_scope_unavailable'}
            cur.execute('SELECT * FROM pp.maintenance_evidence WHERE id=%s AND kind=%s',
                        ('catalog:' + identity['full_designation'], 'catalog_part'))
            row = cur.fetchone()
        if not row:
            return unavailable
        record = {key: row[key] for key in ('id', 'kind', 'title', 'facts', 'source_refs',
                                            'default_retrieval', 'is_local_asset_history')}
        part = record['facts']['part']
        refs = record['source_refs']
        if (digest(record) != row['content_sha256'] or record['is_local_asset_history'] or
                part['sku'] != identity['full_designation'] or
                part['unit_scope'] != 'complete_four_bolt_flange_unit' or not refs or
                any(urlparse(ref['url']).scheme != 'https' or urlparse(ref['url']).hostname != 'www.nsk.com' or
                    not re.fullmatch(r'[0-9a-f]{64}', ref['sha256']) or not ref.get('locator') for ref in refs)):
            return {**unavailable, 'reason': 'food_catalog_evidence_invalid'}
        # Publication provenance and structured-extract version remain distinct.
        record['content_sha256'] = row['content_sha256']
        return dict(status='available', path=refs[0]['url'], sha256=refs[0]['sha256'],
                    source_status='OEM_CATALOG_EXTRACT; fit requires technician and engineering confirmation',
                    snapshot_version=row['content_sha256'],
                    content_snapshot=json.dumps(record, ensure_ascii=False, sort_keys=True),
                    warehouse_id=warehouse_id, category='Bearing')
    except psycopg.Error:
        return {**unavailable, 'reason': 'food_catalog_storage_unavailable'}
    except (KeyError, TypeError, ValueError):
        return {**unavailable, 'reason': 'food_catalog_evidence_invalid'}
