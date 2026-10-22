"""Public demo still enforces request-origin and database generation fences."""
import uuid
import pytest
from test_demo_console import demo


def test_public_demo_without_credentials_preserves_write_guards(demo, monkeypatch):
    _, client = demo
    monkeypatch.setenv('PARTPILOT_DEMO_PUBLIC_ACCESS', 'true')
    monkeypatch.delenv('PARTPILOT_DEMO_PASSWORD', raising=False)
    client.auth = None
    response = client.get('/api/v1/demo/config')
    assert response.status_code == 200
    assert 'www-authenticate' not in response.headers
    config = response.json()
    assert len(config['warehouses']) == 5
    assert client.get('/api/v1/demo/orders').status_code == 200
    reset = {'confirmation': 'RESET DEMO', 'expected_generation': config['generation']}
    assert client.post('/api/v1/demo/reset', json=reset,
                       headers={'Origin': 'https://evil.example'}).status_code == 403
    client.headers.pop('X-PartPilot-Request')
    assert client.post('/api/v1/demo/reset', json=reset).status_code == 403
    client.headers['X-PartPilot-Request'] = 'demo'
    body = dict(config['context'], warehouse_id='SYN-WH-01',
                description='NTN 6200LLU', quantity='1')
    assert client.post('/api/v1/work-orders', json=body, headers={
        'X-PartPilot-Generation': '0', 'Idempotency-Key': uuid.uuid4().hex
    }).status_code == 409
    assert client.post('/api/v1/work-orders', json=body, headers={
        'Idempotency-Key': uuid.uuid4().hex
    }).status_code == 201


def test_runtime_accepts_public_mode_from_scoped_config(monkeypatch):
    from scripts import demo_runtime
    import uvicorn
    monkeypatch.delenv('PARTPILOT_DEMO_PASSWORD', raising=False)
    monkeypatch.delenv('PARTPILOT_DEMO_PUBLIC_ACCESS', raising=False)
    def fake_load(path, allowed):
        if path.endswith('/runtime.env'):
            assert 'PARTPILOT_DEMO_PUBLIC_ACCESS' in allowed
            monkeypatch.setenv('PARTPILOT_DEMO_PUBLIC_ACCESS', 'true')
    monkeypatch.setattr(demo_runtime, 'load', fake_load)
    calls = []
    monkeypatch.setattr(uvicorn, 'run', lambda *args, **kwargs: calls.append(args))
    monkeypatch.setattr(demo_runtime.sys, 'argv', ['demo_runtime.py', 'api'])
    demo_runtime.main()
    assert calls == [('backend.demo.app:app',)]


def test_private_runtime_still_requires_password(monkeypatch):
    from scripts import demo_runtime
    monkeypatch.delenv('PARTPILOT_DEMO_PASSWORD', raising=False)
    monkeypatch.delenv('PARTPILOT_DEMO_PUBLIC_ACCESS', raising=False)
    monkeypatch.setattr(demo_runtime, 'load', lambda *_: None)
    monkeypatch.setattr(demo_runtime.sys, 'argv', ['demo_runtime.py', 'api'])
    with pytest.raises(RuntimeError, match='Missing demo login'):
        demo_runtime.main()
