"""Bounded completions and native tool calls; 9router default, Vertex explicit opt-in.

Tool execution, retries and domain validation belong to callers. No provider fallback.
"""
import json
import math
import os
import re
import time
from typing import Any, Dict, List

import httpx

GATEWAY_BASE_URL = os.environ.get('HERMES_9ROUTER_BASE_URL', 'http://127.0.0.1:20128/v1')
DEFAULT_TIMEOUT_SECONDS = 20.0
MAX_OUTPUT_TOKENS = 4096
MAX_PAYLOAD_BYTES = 1024 * 1024


def _provider():
    value = os.environ.get('PARTPILOT_AI_PROVIDER', '9router').strip().lower()
    return 'vertex_ai' if value == 'vertex' else value


def _model(provider):
    return os.environ.get('PARTPILOT_MODEL') or (
        'gemini-3.8-flash' if provider == 'vertex_ai' else 'ag/gemini-3.8-flash-high')


DEFAULT_MODEL = _model(_provider())


def runtime_timeout() -> float:
    """Each call stays below the worker lease; callers bound multi-turn loops."""
    value = float(os.environ.get('PARTPILOT_GATEWAY_TIMEOUT_SECONDS', '20'))
    if not math.isfinite(value) or not 5 <= value <= 60:
        raise ValueError('Gateway timeout must be between 5 and 60 seconds')
    return value


def redact_secrets(text: str) -> str:
    if not text:
        return ''
    text = re.sub(r'(Bearer\s+)\S+', r'\1[REDACTED]', text, flags=re.IGNORECASE)
    return re.sub(r'sk-[A-Za-z0-9_\-.]{6,}', '[REDACTED_API_KEY]', text)


def get_api_key() -> str:
    return os.environ.get('HERMES_9ROUTER_API_KEY', '').strip()


def _error(model, provider, project_id, error, retriable=False):
    return dict(status='error', model=model, provider=provider, project_id=project_id,
                content='', parsed_json=None, tool_calls=[], assistant_message=None,
                error=error, retriable=retriable)


def _parse_json(content):
    clean = content.strip()
    if clean.startswith('```'):
        clean = re.sub(r'^```(?:json)?\s*', '', clean).split('```', 1)[0].strip()
    try:
        return json.loads(clean)
    except (ValueError, TypeError):
        return None


def _success(model, provider, project_id, content, calls, native=None):
    assistant = dict(role='assistant', content=content, tool_calls=calls)
    if native is not None:
        assistant['vertex_content'] = native
    return dict(status='ok', model=model, provider=provider, project_id=project_id,
                content=content, parsed_json=_parse_json(content), tool_calls=calls,
                assistant_message=assistant, error=None, retriable=False)


def _tool_declarations(tools):
    if not isinstance(tools, list) or len(tools) > 64:
        raise ValueError('Invalid tool declarations')
    result, names = [], set()
    for tool in tools:
        declaration = tool.get('function', tool)
        name = declaration.get('name', '')
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.-]{0,63}', name) or name in names:
            raise ValueError('Invalid or duplicate tool name')
        parameters = declaration.get('parameters', {'type': 'object', 'properties': {}})
        if not isinstance(parameters, dict) or parameters.get('type', 'object') != 'object':
            raise ValueError('Tool parameters must be an object schema')
        result.append(dict(name=name, description=declaration.get('description', ''), parameters=parameters))
        names.add(name)
    return result


def _normalized_call(call):
    function = call.get('function', call)
    arguments = function.get('arguments', {})
    if isinstance(arguments, str):
        arguments = json.loads(arguments)
    if not isinstance(arguments, dict) or not call.get('id') or not function.get('name'):
        raise ValueError('Malformed tool call')
    return dict(id=call['id'], name=function['name'], arguments=arguments)


def _validate(messages, tools, timeout, max_tokens, temperature):
    if not math.isfinite(float(timeout)) or not 0 < timeout <= 60:
        raise ValueError('Gateway timeout must be greater than zero and at most 60 seconds')
    if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or max_tokens < 1:
        raise ValueError('Invalid output token limit')
    if not math.isfinite(float(temperature)) or not 0 <= temperature <= 2:
        raise ValueError('Invalid temperature')
    if not isinstance(messages, list) or not 1 <= len(messages) <= 100:
        raise ValueError('Invalid messages')
    if len(json.dumps([messages, tools]).encode()) > MAX_PAYLOAD_BYTES:
        raise ValueError('Input exceeds gateway limit')
    pending = {}
    for message in messages:
        role = message.get('role')
        if role not in ('system', 'user', 'assistant', 'tool'):
            raise ValueError('Unsupported message role')
        if role == 'assistant':
            for raw_call in message.get('tool_calls', []):
                call = _normalized_call(raw_call)
                if call['id'] in pending:
                    raise ValueError('Duplicate tool call ID')
                pending[call['id']] = call['name']
        elif role == 'tool':
            name = pending.pop(message.get('tool_call_id'), None)
            if not name or (message.get('name') and message['name'] != name):
                raise ValueError('Tool response does not match an outstanding call')
    if pending:
        raise ValueError('Tool responses are missing')
    return _tool_declarations(tools)


def _openai_messages(messages):
    output = []
    for message in messages:
        item = {'role': message['role'], 'content': message.get('content', '')}
        if message['role'] == 'assistant' and message.get('tool_calls'):
            item['tool_calls'] = []
            for raw_call in message['tool_calls']:
                call = _normalized_call(raw_call)
                item['tool_calls'].append(dict(id=call['id'], type='function', function={
                    'name': call['name'], 'arguments': json.dumps(call['arguments'])}))
        if message['role'] == 'tool':
            item['tool_call_id'] = message['tool_call_id']
            if not isinstance(item['content'], str):
                item['content'] = json.dumps(item['content'])
        output.append(item)
    return output


def _router_call(messages, declarations, model, timeout, max_tokens, temperature):
    key = get_api_key()
    if not key:
        return _error(model, '9router', None, 'HERMES_9ROUTER_API_KEY not configured', True)
    payload = dict(model=model, messages=_openai_messages(messages),
                   max_tokens=min(max_tokens, MAX_OUTPUT_TOKENS), temperature=temperature, stream=False)
    if declarations:
        payload['tools'] = [{'type': 'function', 'function': d} for d in declarations]
        payload['tool_choice'] = 'auto'
    with httpx.Client(timeout=timeout) as client:
        response = client.post(os.environ.get('HERMES_9ROUTER_BASE_URL', GATEWAY_BASE_URL).rstrip('/') + '/chat/completions',
                               headers={'Authorization': f'Bearer {key}'}, json=payload)
    if response.status_code != 200:
        return _error(model, '9router', None, f'Gateway HTTP {response.status_code}',
                      response.status_code in (408, 429, 500, 502, 503, 504))
    if len(response.content) > MAX_PAYLOAD_BYTES:
        return _error(model, '9router', None, 'Gateway response exceeds limit')
    data = response.json()
    choices = data.get('choices') or []
    if not choices or not isinstance(choices[0].get('message'), dict):
        return _error(model, '9router', None, 'No completion choices returned by gateway')
    choice = choices[0]
    if choice.get('finish_reason') not in (None, 'stop', 'tool_calls'):
        return _error(model, '9router', None, 'Gateway generation did not finish successfully')
    message = choice['message']
    content = message.get('content') or ''
    calls = [_normalized_call(c) for c in message.get('tool_calls', [])]
    allowed = {d['name'] for d in declarations}
    if any(c['name'] not in allowed for c in calls) or len({c['id'] for c in calls}) != len(calls):
        return _error(model, '9router', None, 'Gateway returned an invalid tool call')
    if not isinstance(content, str) or (not content and not calls):
        return _error(model, '9router', None, 'Gateway returned no usable content')
    return _success(data.get('model', model), '9router', None, content, calls)


def _dispatch(messages, tools, model, timeout, max_tokens, temperature, json_mode):
    provider = _provider()
    model = model or _model(provider)
    project = (os.environ.get('GOOGLE_CLOUD_PROJECT') or os.environ.get('PARTPILOT_VERTEX_PROJECT')
               or 'hackathon-primestep-16') if provider == 'vertex_ai' else None
    try:
        declarations = _validate(messages, tools, timeout, max_tokens, temperature)
        if provider == 'vertex_ai':
            from .vertex_gateway import call_vertex
            return call_vertex(messages, declarations, model, project, timeout, max_tokens, temperature, json_mode)
        if provider == '9router':
            return _router_call(messages, declarations, model, timeout, max_tokens, temperature)
        return _error(model, provider, project, 'Unsupported PARTPILOT_AI_PROVIDER')
    except (httpx.TimeoutException, TimeoutError):
        return _error(model, provider, project, 'Gateway call timed out', True)
    except httpx.HTTPError:
        return _error(model, provider, project, 'Gateway transport failed', True)
    except (ValueError, TypeError, KeyError, AttributeError):
        return _error(model, provider, project, 'Invalid gateway request or response')
    except Exception as exc:
        # Never expose provider bodies, credentials, URLs or exception text.
        return _error(model, provider, project, f'Gateway call failed: {type(exc).__name__}')


def _call(messages, tools, model, timeout, max_tokens, temperature, json_mode):
    started = time.monotonic()
    result = _dispatch(messages, tools, model, timeout, max_tokens, temperature, json_mode)
    result['elapsed_ms'] = round((time.monotonic() - started) * 1000)
    return result


def call_gateway_completion(messages: List[Dict[str, str]], model=None,
                            timeout: float = DEFAULT_TIMEOUT_SECONDS,
                            max_tokens: int = MAX_OUTPUT_TOKENS, temperature: float = 0.0) -> Dict[str, Any]:
    """Preserves the WO/WhatsApp signature and parsed_json result; no automatic retry."""
    return _call(messages, [], model, timeout, max_tokens, temperature, json_mode=True)


def call_agent_turn(messages, tools, model=None, timeout=DEFAULT_TIMEOUT_SECONDS,
                    max_tokens=MAX_OUTPUT_TOKENS, temperature=0.0):
    """Return normalized {id,name,arguments:dict} calls; append assistant_message unchanged.

    Add role=tool messages containing tool_call_id, name, and content (JSON string
    or object). This adapter never executes functions. Native Vertex signatures
    are preserved in assistant_message for subsequent turns.
    """
    return _call(messages, tools, model, timeout, max_tokens, temperature, json_mode=False)


call_gateway = call_gateway_completion
