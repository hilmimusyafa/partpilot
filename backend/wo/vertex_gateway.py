"""Optional native Vertex generateContent transport using ADC; no static tokens.

Supports service accounts, workload identity federation and local user ADC.
Credentials and provider error bodies are never returned or logged.
"""
import json
import os
import re
import time
import uuid
from types import SimpleNamespace

import httpx

from .gateway import MAX_OUTPUT_TOKENS, MAX_PAYLOAD_BYTES, _error, _normalized_call, _success


def _contents(messages):
    system, contents, pending = [], [], {}
    for message in messages:
        role = message['role']
        if role == 'system':
            system.append({'text': message.get('content', '')})
        elif role == 'assistant':
            native = message.get('vertex_content')
            if native is None:
                parts = [{'text': message['content']}] if message.get('content') else []
                parts += [{'functionCall': {'name': c['name'], 'args': c['arguments']}}
                          for c in map(_normalized_call, message.get('tool_calls', []))]
                native = {'role': 'model', 'parts': parts}
            contents.append(native)
            native_calls = [p['functionCall'] for p in native.get('parts', []) if 'functionCall' in p]
            normalized = [_normalized_call(c) for c in message.get('tool_calls', [])]
            if len(native_calls) != len(normalized):
                raise ValueError('Native tool history mismatch')
            for call, original in zip(normalized, native_calls):
                if call['name'] != original['name'] or call['arguments'] != original.get('args', {}):
                    raise ValueError('Native tool history mismatch')
                pending[call['id']] = (call['name'], original.get('id'))
        elif role == 'tool':
            name, native_id = pending.pop(message['tool_call_id'])
            response = message.get('content', {})
            if isinstance(response, str):
                try:
                    response = json.loads(response)
                except ValueError:
                    response = {'result': response}
            if not isinstance(response, dict):
                response = {'result': response}
            part = {'functionResponse': {'name': name, 'response': response}}
            if native_id:
                part['functionResponse']['id'] = native_id
            if contents and contents[-1]['role'] == 'user' and 'functionResponse' in contents[-1]['parts'][0]:
                contents[-1]['parts'].append(part)
            else:
                contents.append({'role': 'user', 'parts': [part]})
        else:
            contents.append({'role': 'user', 'parts': [{'text': message.get('content', '')}]} )
    return system, contents


class _AuthRequest:
    """google.auth transport interface sharing the model call's deadline."""
    def __init__(self, client, deadline):
        self.client, self.deadline = client, deadline

    def __call__(self, url, method='GET', body=None, headers=None, timeout=None, **kwargs):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('Authentication deadline reached')
        response = self.client.request(method, url, content=body, headers=headers,
                                       timeout=min(remaining, timeout) if timeout else remaining)
        return SimpleNamespace(status=response.status_code, data=response.content, headers=response.headers)


def call_vertex(messages, declarations, model, project, timeout, max_tokens, temperature, json_mode):
    location = os.environ.get('GOOGLE_CLOUD_LOCATION', 'global')
    if not re.fullmatch(r'[a-z][a-z0-9-]{4,62}', project):
        return _error(model, 'vertex_ai', project, 'Invalid Google Cloud project ID')
    if not re.fullmatch(r'[a-z0-9-]{1,40}', location) or not re.fullmatch(r'gemini-[A-Za-z0-9_.-]{1,120}', model):
        return _error(model, 'vertex_ai', project, 'Invalid native Vertex model or location')
    host = 'aiplatform.googleapis.com' if location == 'global' else f'{location}-aiplatform.googleapis.com'
    url = f'https://{host}/v1/projects/{project}/locations/{location}/publishers/google/models/{model}:generateContent'
    system, contents = _contents(messages)
    payload = {'contents': contents, 'generationConfig': {
        'maxOutputTokens': min(max_tokens, MAX_OUTPUT_TOKENS), 'temperature': temperature}}
    if system:
        payload['systemInstruction'] = {'parts': system}
    if json_mode:
        payload['generationConfig']['responseMimeType'] = 'application/json'
    if declarations:
        payload['tools'] = [{'functionDeclarations': [
            {'name': d['name'], 'description': d['description'], 'parametersJsonSchema': d['parameters']}
            for d in declarations]}]
        payload['toolConfig'] = {'functionCallingConfig': {'mode': 'AUTO'}}
    try:
        import google.auth
        from google.auth.exceptions import DefaultCredentialsError, RefreshError, TransportError
    except ImportError:
        return _error(model, 'vertex_ai', project, 'Vertex requires the google-auth dependency')
    deadline = time.monotonic() + timeout
    try:
        with httpx.Client(timeout=timeout) as client:
            request = _AuthRequest(client, deadline)
            credentials, _ = google.auth.default(request=request,
                scopes=['https://www.googleapis.com/auth/cloud-platform'], quota_project_id=project)
            headers = {'Content-Type': 'application/json'}
            credentials.before_request(request, 'POST', url, headers)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('Authentication deadline reached')
            response = client.post(url, headers=headers, json=payload, timeout=remaining)
    except DefaultCredentialsError:
        return _error(model, 'vertex_ai', project, 'Vertex ADC not configured; configure Application Default Credentials')
    except RefreshError:
        return _error(model, 'vertex_ai', project, 'Vertex ADC refresh failed; verify credential access')
    except TransportError:
        return _error(model, 'vertex_ai', project, 'Vertex authentication transport failed', True)
    if response.status_code != 200:
        return _error(model, 'vertex_ai', project, f'Vertex HTTP {response.status_code}',
                      response.status_code in (408, 429, 500, 502, 503, 504))
    if len(response.content) > MAX_PAYLOAD_BYTES:
        return _error(model, 'vertex_ai', project, 'Vertex response exceeds limit')
    data = response.json()
    candidates = data.get('candidates') or []
    if not candidates or candidates[0].get('finishReason') != 'STOP':
        return _error(model, 'vertex_ai', project, 'Vertex returned blocked, incomplete or missing content')
    native = candidates[0].get('content') or {}
    content, calls = [], []
    allowed = {d['name'] for d in declarations}
    for part in native.get('parts', []):
        if 'text' in part and not part.get('thought'):
            content.append(part['text'])
        if 'functionCall' in part:
            function = part['functionCall']
            if function.get('name') not in allowed or not isinstance(function.get('args', {}), dict):
                return _error(model, 'vertex_ai', project, 'Vertex returned an invalid tool call')
            calls.append({'id': function.get('id') or 'vertex_' + uuid.uuid4().hex,
                          'name': function['name'], 'arguments': function.get('args', {})})
    text = ''.join(content)
    if (not text and not calls) or len({c['id'] for c in calls}) != len(calls):
        return _error(model, 'vertex_ai', project, 'Vertex returned no usable content or duplicate calls')
    result = _success(data.get('modelVersion', model), 'vertex_ai', project, text, calls, native)
    if json_mode and not isinstance(result['parsed_json'], (dict, list)):
        return _error(model, 'vertex_ai', project, 'Vertex returned invalid structured JSON')
    return result
