"""Read-only evidence capabilities exposed to the model. No SQL or arbitrary URLs."""
import json
import re

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class CaseQuery(BaseModel):
    model_config = ConfigDict(extra='forbid')
    query: str = Field(min_length=1, max_length=300)


class PartQuery(BaseModel):
    model_config = ConfigDict(extra='forbid')
    sku: str = Field(min_length=1, max_length=80)


class TroubleshootingQuery(BaseModel):
    model_config = ConfigDict(extra='forbid')
    damage_type: str = Field(min_length=1, max_length=80)


TOOLS = [
    {'type': 'function', 'function': {'name': 'retrieve_cases', 'description': 'Find external OEM published conveyor cases or selected economic benchmarks. Not local asset work orders.',
      'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'English/Indonesian symptoms or case ID, e.g. conveyor washdown corrosion'}}, 'required': ['query'], 'additionalProperties': False}}},
    {'type': 'function', 'function': {'name': 'read_catalog_part', 'description': 'Read exact complete housed-unit catalog evidence. Available: PSF20CR (proposed demo exact), PSF20/LP99 (unapproved engineering candidate). Insert-only codes are not assemblies.',
      'parameters': {'type': 'object', 'properties': {'sku': {'type': 'string'}}, 'required': ['sku'], 'additionalProperties': False}}},
    {'type': 'function', 'function': {'name': 'read_troubleshooting', 'description': 'Read OEM possible causes and inspection guidance; available damage type rust_and_corrosion. This cannot confirm a diagnosis.',
      'parameters': {'type': 'object', 'properties': {'damage_type': {'type': 'string'}}, 'required': ['damage_type'], 'additionalProperties': False}}},
]


def _evidence_payload(row):
    # Database ingestion timestamps describe storage, not source publication.
    # Expose the bounded, JSON-native evidence contract only.
    return {key: row[key] for key in ('id', 'kind', 'title', 'facts', 'source_refs',
                                     'default_retrieval', 'is_local_asset_history', 'content_sha256')}


def execute_tool(name, arguments, store):
    try:
        if name == 'retrieve_cases':
            query = CaseQuery.model_validate(arguments).query.lower()
            translations = {'konveyor': 'conveyor', 'karat': 'corrosion', 'korosi': 'corrosion',
                            'pencucian': 'wash', 'bantalan': 'bearing', 'biaya': 'cost', 'air': 'water'}
            tokens = [translations.get(t, t) for t in re.findall(r'[\w-]+', query) if len(t) > 2]
            rows = [_evidence_payload(row) for row in store.list_evidence() if row['kind'] in ('published_case', 'economic_case') and row['default_retrieval']]
            scored = [(sum(token in json.dumps(row, ensure_ascii=False).lower() for token in tokens), row) for row in rows]
            selected = [row for score, row in sorted(scored, key=lambda pair: (-pair[0], pair[1]['id'])) if score > 0][:3]
        elif name == 'read_catalog_part':
            sku = PartQuery.model_validate(arguments).sku.strip().upper()
            row = store.get_evidence('catalog:' + sku)
            selected = [_evidence_payload(row)] if row and row['kind'] == 'catalog_part' else []
        elif name == 'read_troubleshooting':
            damage = TroubleshootingQuery.model_validate(arguments).damage_type.strip().lower()
            row = store.get_evidence('troubleshooting:' + damage)
            selected = [_evidence_payload(row)] if row and row['kind'] == 'troubleshooting' else []
        else:
            return {'status': 'rejected', 'error': 'unknown_read_only_tool', 'evidence': []}
    except (ValidationError, TypeError, ValueError):
        return {'status': 'rejected', 'error': 'invalid_tool_arguments', 'evidence': []}
    return {'status': 'ok' if selected else 'not_found', 'evidence': selected,
            'scope': 'external_published_evidence_not_local_asset_history'}
