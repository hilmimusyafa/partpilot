import pytest


def test_only_authorized_number_is_deliverable(monkeypatch):
    from backend.whatsapp.safety import require_allowed_recipient
    monkeypatch.setenv('PARTPILOT_WA_ALLOWED_RECIPIENTS','6282178830078')
    assert require_allowed_recipient('082178830078') == '6282178830078'
    assert require_allowed_recipient('+62 821-7883-0078') == '6282178830078'
    with pytest.raises(ValueError): require_allowed_recipient('6281234567890')


def test_unconfigured_allowlist_fails_closed(monkeypatch):
    from backend.whatsapp.safety import require_allowed_recipient
    monkeypatch.delenv('PARTPILOT_WA_ALLOWED_RECIPIENTS',raising=False)
    with pytest.raises(ValueError): require_allowed_recipient('6282178830078')


@pytest.mark.parametrize('path', ['/check', '/send'])
def test_bridge_blocks_other_recipient_before_opening_http_client(monkeypatch, path):
    from backend.whatsapp import service
    from backend.procurement.repository import ProcurementError
    monkeypatch.setenv('PARTPILOT_WA_ALLOWED_RECIPIENTS', '6282178830078')
    monkeypatch.setenv('PARTPILOT_WA_INTERNAL_TOKEN', 'test-only-internal-token')
    def forbidden_client(**kwargs):
        pytest.fail('Blocked recipients must never reach the HTTP boundary')
    monkeypatch.setattr(service.httpx, 'Client', forbidden_client)
    with pytest.raises(ProcurementError) as exc:
        service.bridge(path, {'phone': '6281234567890', 'event_id': 'fixture', 'text': 'fixture'})
    assert exc.value.code == 'recipient_not_allowlisted'


def test_bridge_normalizes_allowed_recipient_and_preserves_message(monkeypatch):
    import json
    import httpx
    from backend.whatsapp import service
    monkeypatch.setenv('PARTPILOT_WA_ALLOWED_RECIPIENTS', '6282178830078')
    monkeypatch.setenv('PARTPILOT_WA_INTERNAL_TOKEN', 'test-only-internal-token')
    requests = []
    def handle(request):
        requests.append(request)
        return httpx.Response(200, json={'status': 'sent', 'message_id': 'fixture-only'})
    client_type = httpx.Client
    monkeypatch.setattr(service.httpx, 'Client', lambda **kwargs: client_type(
        transport=httpx.MockTransport(handle), **kwargs))
    result = service.bridge('/send', {'phone': '082178830078', 'event_id': 'event-fixture', 'text': 'test fixture'})
    assert result == {'status': 'sent', 'message_id': 'fixture-only'}
    assert len(requests) == 1
    assert json.loads(requests[0].content) == {
        'phone': '6282178830078', 'event_id': 'event-fixture', 'text': 'test fixture'}
