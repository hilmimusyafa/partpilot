import test from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { createHandler } from '../src/http.js';

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
