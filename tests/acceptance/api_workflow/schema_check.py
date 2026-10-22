"""Read-only private contract validation; never fetch references or print raw contract."""
import hashlib
import json
from pathlib import Path
import sys

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

HERE = Path(__file__).resolve().parent
SOURCE = Path('/srv/hermes-control/private/partpilot/design/backend-openapi-draft.yaml')


def load():
    baseline = json.loads((HERE / 'BASELINE.json').read_text())
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == baseline['private_sources'][str(SOURCE)], 'Private contract drift'
    doc = yaml.safe_load(SOURCE.read_text())
    assert doc['openapi'] == '3.1.0'
    return doc


def validator(doc, name):
    # In-memory resource; external references are not permitted.
    resource = Resource.from_contents({'$schema': 'https://json-schema.org/draft/2020-12/schema', **doc})
    registry = Registry().with_resource('urn:partpilot:contract', resource)
    return Draft202012Validator({'$ref': 'urn:partpilot:contract#/components/schemas/' + name},
                               registry=registry, format_checker=FormatChecker())


def main():
    doc = load()
    if len(sys.argv) == 2:
        validator(doc, sys.argv[1]).validate(json.load(sys.stdin))
        return
    ids = []
    examples = 0
    for schema in doc['components']['schemas'].values():
        Draft202012Validator.check_schema(schema)
    def visit(value):
        if isinstance(value, dict):
            if '$ref' in value:
                ref = value['$ref']
                assert ref.startswith('#/'), 'External ref prohibited'
                target = doc
                for part in ref[2:].split('/'):
                    target = target[part.replace('~1', '/').replace('~0', '~')]
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(doc)
    for path, methods in doc['paths'].items():
        for method, operation in methods.items():
            ids.append(operation['operationId'])
            for media in operation.get('requestBody', {}).get('content', {}).values():
                if 'example' in media:
                    name = media['schema']['$ref'].split('/')[-1]
                    validator(doc, name).validate(media['example'])
                    examples += 1
            for response in operation['responses'].values():
                if '$ref' in response:
                    response = doc['components']['responses'][response['$ref'].split('/')[-1]]
                for media in response.get('content', {}).values():
                    if 'example' in media:
                        name = media['schema']['$ref'].split('/')[-1]
                        validator(doc, name).validate(media['example'])
                        examples += 1
    assert len(ids) == len(set(ids)) == 9
    print(json.dumps({'schema': 'PASS', 'operations': len(ids), 'validated_examples_including_reused_errors': examples}))


if __name__ == '__main__':
    main()
