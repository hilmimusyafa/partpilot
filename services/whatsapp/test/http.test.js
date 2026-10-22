import test from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { createHandler } from '../src/http.js';
import { BridgeCore } from '../src/core.js';

test('every route authenticates before actions and suppresses caching of QR', async t => {
  let sends = 0;
  const token = 't'.repeat(32);
  const transport = { status: () => ({ connection: 'disconnected', qr_data_url: null, enabled: true }), connect: async () => {} };
  const core = { inbox: () => [], ack: () => {}, send: async () => { sends++; return { status: 'sent' }; } };
  const server = createServer(createHandler({ token, transport, core }));
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  t.after(() => new Promise(resolve => server.close(resolve)));
  const base = `http://127.0.0.1:${server.address().port}`;
  for (const path of ['/status', '/connect', '/check', '/send', '/inbox', '/inbox/ack', '/unknown']) {
    assert.equal((await fetch(base + path, { method: path === '/status' || path === '/inbox' ? 'GET' : 'POST' })).status, 401);
  }
  assert.equal(sends, 0);
  const result = await fetch(base + '/status', { headers: { Authorization: `Bearer ${token}` } });
  assert.equal(result.status, 200);
  assert.equal(result.headers.get('cache-control'), 'no-store');
  assert.equal((await result.json()).connection, 'disconnected');
  const malformed = await fetch(base + '/send', { method: 'POST', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }, body: '{' });
  assert.equal(malformed.status, 400);
});

test('authenticated HTTP cannot check or send to a recipient outside the bridge allowlist', async t => {
  let sends = 0, checks = 0, saves = 0;
  const token = 'fixture-authentication-token-32-characters';
  const state = { outbox: {}, inbox: {}, seen: {} };
  const core = new BridgeCore({ state, save: () => { saves++; } }, {
    enabled: true, recipients: ['6282178830078'], connected: () => true,
    send: async () => { sends++; return { key: { id: 'fixture-only' } }; },
  });
  const transport = {
    check: async () => { checks++; return { registered: true }; },
    status: () => ({ connection: 'connected', enabled: true }),
  };
  const server = createServer(createHandler({ token, transport, core }));
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  t.after(() => new Promise(resolve => server.close(resolve)));
  const base = `http://127.0.0.1:${server.address().port}`;
  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
  for (const path of ['/check', '/send']) {
    const response = await fetch(base + path, { method: 'POST', headers,
      body: JSON.stringify({ event_id: 'fixture', phone: '6281234567890', text: 'fixture' }) });
    assert.equal(response.status, 403);
    assert.deepEqual(await response.json(), { error: 'recipient_not_allowed' });
  }
  assert.equal(sends, 0);
  assert.equal(checks, 0);
  assert.equal(saves, 0);
  assert.deepEqual(state.outbox, {});
  // Valid authentication and the allowed recipient reach the same real route.
  const allowed = await fetch(base + '/check', { method: 'POST', headers,
    body: JSON.stringify({ phone: '6282178830078' }) });
  assert.equal(allowed.status, 200);
  assert.equal(checks, 1);
});
