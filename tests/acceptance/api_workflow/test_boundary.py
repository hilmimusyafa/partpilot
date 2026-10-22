import pytest
from helpers import BASE, error, intake_body, post


@pytest.mark.parametrize('header', ['X-Org-ID', 'Authorization', 'X-Caller-Role'])
def test_forged_context_header_rejected(rig, header):
    before = rig.repo.snapshot()
    response = rig.client.post(BASE, json=intake_body(), headers={header: 'SYN-forged', 'Idempotency-Key': 'SYN-guard-0001'})
    error(response, 400, 'CONTEXT_REJECTED')
    assert rig.repo.snapshot() == before


@pytest.mark.parametrize('headers', [{'Origin': 'null'}, {'Origin': 'https://hostile.invalid'}, {'Host': 'hostile.invalid'}])
def test_hostile_boundary_no_mutation(rig, headers):
    before = rig.repo.snapshot()
    response = rig.client.post(BASE, json=intake_body(), headers={**headers, 'Idempotency-Key': 'SYN-guard-0001'})
    error(response, 403, 'LOCAL_ONLY')
    assert rig.repo.snapshot() == before


@pytest.mark.parametrize('mode', ['media', 'large', 'malformed'])
def test_transport_errors_sanitized(rig, mode):
    before = rig.repo.snapshot()
    content, media, status, code = {
        'media': ('SYN-text', 'text/plain', 415, 'UNSUPPORTED_MEDIA_TYPE'),
        'large': ('{"x":"' + 'x' * (256 * 1024) + '"}', 'application/json', 413, 'REQUEST_TOO_LARGE'),
        'malformed': ('{', 'application/json', 422, 'VALIDATION_ERROR'),
    }[mode]
    response = rig.client.post(BASE, content=content, headers={'Content-Type': media, 'Idempotency-Key': 'SYN-guard-0001'})
    error(response, status, code)
    assert rig.repo.snapshot() == before
