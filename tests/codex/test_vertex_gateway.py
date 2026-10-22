"""Gateway boundary tests: real request encoding/parsing, fake HTTP and ADC only."""
import json

import httpx
import pytest

from backend.wo import gateway


def install_vertex_transport(monkeypatch, responses):
    from backend.wo import vertex_gateway
    import google.auth
    from google.auth.credentials import Credentials

    class LocalCredentials(Credentials):
        def __init__(self):
            super().__init__()
            self.token = 'test-only-credential-never-returned'

        def refresh(self, request):
            raise AssertionError('Test credentials must not contact an auth server')

    monkeypatch.setattr(google.auth, 'default', lambda **kwargs: (LocalCredentials(), 'wrong-adc-project'))
    requests = []
    def handle(request):
        requests.append(request)
        response = responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response
    client_type = httpx.Client
    monkeypatch.setattr(vertex_gateway.httpx, 'Client', lambda **kwargs: client_type(
        transport=httpx.MockTransport(handle), **kwargs))
    monkeypatch.setenv('GOOGLE_CLOUD_PROJECT', 'hackathon-primestep-16')
    monkeypatch.setenv('GOOGLE_CLOUD_LOCATION', 'global')
    monkeypatch.setenv('PARTPILOT_AI_PROVIDER', 'vertex_ai')
    monkeypatch.delenv('PARTPILOT_MODEL', raising=False)
    return requests


def completion(text='{"facts": []}', **candidate):
    return httpx.Response(200, json={'modelVersion': 'gemini-3.8-flash', 'candidates': [{
        'content': {'role': 'model', 'parts': [{'text': text}]},
        'finishReason': 'STOP', **candidate}]})


def test_completion_uses_vertex_project_adc_and_json_mode(monkeypatch):
    # Catches stale router URL/key/model routing and loss of the existing parsed_json contract.
    assert hasattr(gateway, 'call_agent_turn'), 'native agent gateway is missing'
    requests = install_vertex_transport(monkeypatch, [completion()])
    result = gateway.call_gateway_completion([
        {'role': 'system', 'content': 'Return facts as JSON'},
        {'role': 'user', 'content': 'bearing noise'},
    ], model='gemini-3.8-flash', max_tokens=9000)
    assert result['status'] == 'ok'
    assert result['parsed_json'] == {'facts': []}
    assert result['provider'] == 'vertex_ai'
    assert result['project_id'] == 'hackathon-primestep-16'
    assert result['model'] == 'gemini-3.8-flash'
    assert isinstance(result['elapsed_ms'], int) and result['elapsed_ms'] >= 0
    request = requests[0]
    assert str(request.url) == ('https://aiplatform.googleapis.com/v1/projects/'
        'hackathon-primestep-16/locations/global/publishers/google/models/gemini-3.8-flash:generateContent')
    assert request.headers['authorization'] == 'Bearer test-only-credential-never-returned'
    body = json.loads(request.content)
    assert body['systemInstruction'] == {'parts': [{'text': 'Return facts as JSON'}]}
    assert body['contents'] == [{'role': 'user', 'parts': [{'text': 'bearing noise'}]}]
    assert body['generationConfig']['responseMimeType'] == 'application/json'
    assert body['generationConfig']['maxOutputTokens'] == 4096
    assert 'test-only-credential' not in json.dumps(result)


def test_native_parallel_calls_preserve_signatures_and_link_tool_results(monkeypatch):
    assert hasattr(gateway, 'call_agent_turn'), 'native agent gateway is missing'
    native = {'role': 'model', 'parts': [
        {'functionCall': {'name': 'search_history', 'args': {'query': 'washdown'}}, 'thoughtSignature': 'opaque-signature'},
        {'functionCall': {'name': 'get_catalog', 'args': {'sku': 'PSF20CR'}}},
    ]}
    requests = install_vertex_transport(monkeypatch, [httpx.Response(200, json={
        'modelVersion': 'gemini-3.8-flash', 'candidates': [{'content': native, 'finishReason': 'STOP'}]}),
        completion('Evidence supports an inspection.')])
    tools = [{'type': 'function', 'function': {'name': 'search_history', 'description': 'Search published history',
        'parameters': {'type': 'object', 'properties': {'query': {'type': 'string'}}, 'required': ['query']}}},
        {'name': 'get_catalog', 'parameters': {'type': 'object', 'properties': {'sku': {'type': 'string'}}}}]
    messages = [{'role': 'user', 'content': 'Investigate washdown'}]
    first = gateway.call_agent_turn(messages, tools)
    assert first['status'] == 'ok'
    assert first['tool_calls'][0]['arguments'] == {'query': 'washdown'}
    assert first['tool_calls'][0]['id'] != first['tool_calls'][1]['id']
    assert first['assistant_message']['vertex_content'] == native
    messages.append(first['assistant_message'])
    for call in first['tool_calls']:
        messages.append({'role': 'tool', 'tool_call_id': call['id'], 'name': call['name'],
            'content': json.dumps({'records': [call['name']]})})
    final = gateway.call_agent_turn(messages, tools)
    assert final['content'] == 'Evidence supports an inspection.'
    body = json.loads(requests[1].content)
    assert body['contents'][1] == native
    assert body['contents'][2] == {'role': 'user', 'parts': [
        {'functionResponse': {'name': 'search_history', 'response': {'records': ['search_history']}}},
        {'functionResponse': {'name': 'get_catalog', 'response': {'records': ['get_catalog']}}},
    ]}
    assert 'responseMimeType' not in body['generationConfig']
    assert body['tools'][0]['functionDeclarations'][0]['name'] == 'search_history'


@pytest.mark.parametrize('status,retriable', [(400, False), (401, False), (403, False), (429, True), (503, True)])
def test_provider_errors_are_classified_without_echoing_provider_body(monkeypatch, status, retriable):
    assert hasattr(gateway, 'call_agent_turn'), 'native agent gateway is missing'
    requests = install_vertex_transport(monkeypatch, [httpx.Response(status, text='private_key=never-echo-me')])
    result = gateway.call_agent_turn([{'role': 'user', 'content': 'inspect'}], [])
    assert result['status'] == 'error'
    assert result['retriable'] is retriable
    assert 'never-echo-me' not in json.dumps(result)
    assert len(requests) == 1  # Retries belong to the bounded caller, never this adapter.


def test_missing_adc_is_actionable_and_does_not_echo_exception(monkeypatch):
    assert hasattr(gateway, 'call_agent_turn'), 'native agent gateway is missing'
    install_vertex_transport(monkeypatch, [])
    import google.auth
    from google.auth.exceptions import DefaultCredentialsError
    def absent(**kwargs):
        raise DefaultCredentialsError('secret-credential-file-contents')
    monkeypatch.setattr(google.auth, 'default', absent)
    result = gateway.call_gateway_completion([{'role': 'user', 'content': 'facts'}])
    assert result['status'] == 'error'
    assert result['retriable'] is False
    assert 'ADC' in result['error']
    assert 'secret-credential' not in json.dumps(result)


@pytest.mark.parametrize('candidate', [
    {'finishReason': 'MAX_TOKENS'}, {'finishReason': 'SAFETY'},
    {'content': {'role': 'model', 'parts': []}},
])
def test_truncated_blocked_or_empty_candidates_are_not_success(monkeypatch, candidate):
    assert hasattr(gateway, 'call_agent_turn'), 'native agent gateway is missing'
    install_vertex_transport(monkeypatch, [completion(**candidate)])
    result = gateway.call_gateway_completion([{'role': 'user', 'content': 'facts'}])
    assert result['status'] == 'error'
    assert result['parsed_json'] is None


def test_invalid_json_cannot_be_reported_as_structured_success(monkeypatch):
    assert hasattr(gateway, 'call_agent_turn'), 'native agent gateway is missing'
    install_vertex_transport(monkeypatch, [completion('not JSON')])
    result = gateway.call_gateway_completion([{'role': 'user', 'content': 'facts'}])
    assert result['status'] == 'error'
    assert result['parsed_json'] is None


@pytest.mark.parametrize('timeout', [0, -1, 61, float('nan'), float('inf')])
def test_invalid_call_budget_rejected_before_auth(monkeypatch, timeout):
    assert hasattr(gateway, 'call_agent_turn'), 'native agent gateway is missing'
    requests = install_vertex_transport(monkeypatch, [])
    result = gateway.call_agent_turn([{'role': 'user', 'content': 'facts'}], [], timeout=timeout)
    assert result['status'] == 'error'
    assert not requests


def test_unmatched_tool_response_rejected_before_network(monkeypatch):
    assert hasattr(gateway, 'call_agent_turn'), 'native agent gateway is missing'
    requests = install_vertex_transport(monkeypatch, [])
    result = gateway.call_agent_turn([{'role': 'user', 'content': 'facts'},
        {'role': 'tool', 'tool_call_id': 'invented', 'name': 'search_history', 'content': '{}'}], [])
    assert result['status'] == 'error'
    assert not requests


def test_legacy_router_model_or_provider_fails_closed(monkeypatch):
    assert hasattr(gateway, 'call_agent_turn'), 'native agent gateway is missing'
    requests = install_vertex_transport(monkeypatch, [])
    result = gateway.call_gateway_completion([{'role': 'user', 'content': 'facts'}], model='ag/gemini-3.8-flash-high')
    assert result['status'] == 'error'
    monkeypatch.setenv('PARTPILOT_AI_PROVIDER', 'unsupported_provider')
    result = gateway.call_agent_turn([{'role': 'user', 'content': 'facts'}], [])
    assert result['status'] == 'error'
    assert not requests


def test_router_native_calls_preserve_openai_ids_and_tool_response(monkeypatch):
    assert hasattr(gateway, 'call_agent_turn'), 'native agent gateway is missing'
    monkeypatch.setenv('PARTPILOT_AI_PROVIDER', '9router')
    monkeypatch.delenv('PARTPILOT_MODEL', raising=False)
    monkeypatch.setenv('HERMES_9ROUTER_API_KEY', 'test-router-secret')
    monkeypatch.setenv('HERMES_9ROUTER_BASE_URL', 'http://router.test/v1')
    requests = []
    def handle(request):
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(200, json={'model': 'ag/gemini-3.8-flash-high', 'choices': [{
                'finish_reason': 'tool_calls', 'message': {'role': 'assistant', 'content': None,
                'tool_calls': [{'id': 'call_original', 'type': 'function', 'function': {
                    'name': 'search_history', 'arguments': '{"query":"washdown"}'}}]}}]})
        return httpx.Response(200, json={'choices': [{'finish_reason': 'stop',
            'message': {'role': 'assistant', 'content': 'Inspect seal condition.'}}]})
    client_type = httpx.Client
    monkeypatch.setattr(gateway.httpx, 'Client', lambda **kwargs: client_type(
        transport=httpx.MockTransport(handle), **kwargs))
    tools = [{'name': 'search_history', 'parameters': {'type': 'object', 'properties': {}}}]
    messages = [{'role': 'user', 'content': 'Inspect conveyor'}]
    first = gateway.call_agent_turn(messages, tools)
    assert first['provider'] == '9router'
    assert first['project_id'] is None
    assert first['tool_calls'] == [{'id': 'call_original', 'name': 'search_history', 'arguments': {'query': 'washdown'}}]
    messages += [first['assistant_message'], {'role': 'tool', 'name': 'search_history',
        'tool_call_id': 'call_original', 'content': '{"records":[]}'}]
    final = gateway.call_agent_turn(messages, tools)
    assert final['status'] == 'ok'
    assert final['content'] == 'Inspect seal condition.'
    body = json.loads(requests[1].content)
    assert body['messages'][1]['tool_calls'][0]['function']['arguments'] == '{"query": "washdown"}'
    assert body['messages'][2]['tool_call_id'] == 'call_original'
    assert body['tools'][0]['type'] == 'function'
    assert body['tool_choice'] == 'auto'
    assert 'test-router-secret' not in json.dumps(final)


def test_router_completion_keeps_existing_fenced_json_contract(monkeypatch):
    monkeypatch.delenv('PARTPILOT_AI_PROVIDER', raising=False)
    monkeypatch.delenv('PARTPILOT_MODEL', raising=False)
    monkeypatch.setenv('HERMES_9ROUTER_API_KEY', 'test-router-secret')
    client_type = httpx.Client
    monkeypatch.setattr(gateway.httpx, 'Client', lambda **kwargs: client_type(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={'choices': [{
            'message': {'content': '```json\n{"facts": []}\n```'}, 'finish_reason': 'stop'}]})), **kwargs))
    result = gateway.call_gateway_completion([{'role': 'user', 'content': 'facts'}])
    assert result['status'] == 'ok'
    assert result['parsed_json'] == {'facts': []}
    assert result['provider'] == '9router'


def test_timeout_is_retriable_without_exception_details(monkeypatch):
    install_vertex_transport(monkeypatch, [httpx.ReadTimeout('private-auth-data')])
    result = gateway.call_agent_turn([{'role': 'user', 'content': 'facts'}], [])
    assert result['status'] == 'error'
    assert result['retriable'] is True
    assert 'private-auth' not in json.dumps(result)


def test_adc_refresh_transport_and_provider_share_one_call_budget(monkeypatch):
    from backend.wo import vertex_gateway
    import google.auth
    from google.auth.credentials import Credentials
    requests = install_vertex_transport(monkeypatch, [httpx.Response(200, json={'access_token': 'fresh-test-token'}), completion()])
    class RefreshCredentials(Credentials):
        def refresh(self, request):
            response = request('https://oauth2.googleapis.com/token', method='POST', body=b'fixture', timeout=120)
            assert response.status == 200
            self.token = json.loads(response.data)['access_token']
    monkeypatch.setattr(google.auth, 'default', lambda **kwargs: (RefreshCredentials(), None))
    result = gateway.call_gateway_completion([{'role': 'user', 'content': 'facts'}], timeout=5)
    assert result['status'] == 'ok'
    assert len(requests) == 2
    assert 0 < requests[0].extensions['timeout']['read'] <= 5
    assert 0 < requests[1].extensions['timeout']['read'] <= requests[0].extensions['timeout']['read']
    assert requests[1].headers['authorization'] == 'Bearer fresh-test-token'
    assert 'fresh-test-token' not in json.dumps(result)
