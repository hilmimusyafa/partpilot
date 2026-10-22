import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync } from 'node:fs';
import { join } from 'node:path';
import { DurableStore, BridgeCore } from '../src/core.js';

const phone = '12025550123'; // reserved fictional test number
const event = { event_id: 'event-1', phone, text: 'Status testing' };
function fixture(t, send = async () => ({ key: { id: 'wa-1' } })) {
  const dir = mkdtempSync(join(process.cwd(), '.test-state-'));
  t.after(() => rmSync(dir, { recursive: true, force: true }));
  const store = new DurableStore(dir);
  const options = { enabled: true, recipients: [phone], connected: () => true, send, timeoutMs: 30 };
  return { dir, store, options, core: new BridgeCore(store, options) };
}

test('persisted successful send is returned after restart without another transport call', async t => {
  let sent = 0;
  const f = fixture(t, async (jid, text) => {
    assert.equal(jid, '12025550123@s.whatsapp.net');
    assert.equal(text, 'Status testing');
    sent++; return { key: { id: 'wa-1' } };
  });
  assert.deepEqual(await f.core.send(event), { status: 'sent', message_id: 'wa-1' });
  const restarted = new BridgeCore(new DurableStore(f.dir), f.options);
  assert.deepEqual(await restarted.send(event), { status: 'sent', message_id: 'wa-1' });
  assert.equal(sent, 1);
  await assert.rejects(restarted.send({ ...event, text: 'different' }), { statusCode: 409 });
});

test('reservation survives a crash and is never automatically sent again', async t => {
  let sent = 0;
  const f = fixture(t, async () => { sent++; return new Promise(() => {}); });
  const pending = f.core.send(event);
  const restarted = new BridgeCore(new DurableStore(f.dir), f.options);
  assert.deepEqual(await restarted.send(event), { status: 'uncertain' });
  assert.deepEqual(await pending, { status: 'uncertain' });
  assert.equal(sent, 1);
});

test('concurrent event duplicates reserve once; unconnected work remains retryable', async t => {
  let resolve;
  const f = fixture(t, () => new Promise(r => { resolve = r; }));
  const first = f.core.send(event);
  assert.deepEqual(await f.core.send(event), { status: 'pending' });
  resolve({ key: { id: 'wa-1' } });
  assert.equal((await first).status, 'sent');
  const offline = new BridgeCore(f.store, { ...f.options, connected: () => false });
  assert.deepEqual(await offline.send({ ...event, event_id: 'event-2' }), { status: 'pending' });
  assert.equal(f.store.state.outbox['event-2'], undefined);
});

test('disabled, unallowlisted and oversize sends are rejected before transport', async t => {
  const f = fixture(t, () => assert.fail('must never send'));
  await assert.rejects(f.core.send({ ...event, phone: '12025550999' }), { statusCode: 403 });
  await assert.rejects(f.core.send({ ...event, text: 'x'.repeat(8001) }), { statusCode: 400 });
  await assert.rejects(new BridgeCore(f.store, { ...f.options, enabled: false }).send(event), { statusCode: 503 });
});

test('inbound persists once until ack; own, groups, history and unknown phones are excluded', async t => {
  const f = fixture(t);
  const message = { key: { id: 'in-1', remoteJid: `${phone}@s.whatsapp.net`, fromMe: false }, message: { conversation: 'need stock' }, messageTimestamp: 1700000000 };
  await f.core.ingest(message, 'notify');
  await f.core.ingest(message, 'notify');
  await f.core.ingest({ ...message, key: { ...message.key, id: 'own', fromMe: true } }, 'notify');
  await f.core.ingest({ ...message, key: { ...message.key, id: 'group', remoteJid: '123@g.us' } }, 'notify');
  await f.core.ingest({ ...message, key: { ...message.key, id: 'other', remoteJid: '12025550999@s.whatsapp.net' } }, 'notify');
  await f.core.ingest({ ...message, key: { ...message.key, id: 'history' } }, 'append');
  const restarted = new BridgeCore(new DurableStore(f.dir), f.options);
  const rows = restarted.inbox();
  assert.equal(rows.length, 1);
  assert.equal(rows[0].phone, phone);
  assert.equal(rows[0].text, 'need stock');
  assert.equal(rows[0].received_at, '2023-11-14T22:13:20.000Z');
  restarted.ack([rows[0].message_id]);
  const again = new BridgeCore(new DurableStore(f.dir), f.options);
  await again.ingest(message, 'notify');
  assert.deepEqual(again.inbox(), []);
});

test('LID inbound resolves through mapping and unmapped LID is ignored', async t => {
  const f = fixture(t);
  const message = { key: { id: 'lid-1', remoteJid: '123456@lid', fromMe: false }, message: { extendedTextMessage: { text: 'hello' } } };
  await f.core.ingest(message, 'notify', async () => undefined);
  assert.equal(f.core.inbox().length, 0);
  await f.core.ingest(message, 'notify', async lid => {
    assert.equal(lid, '123456@lid'); return `${phone}@s.whatsapp.net`;
  });
  assert.equal(f.core.inbox()[0].phone, phone);
});

test('transport rejection and late timeout completion remain uncertain after restart', async t => {
  const f = fixture(t, async () => { throw new Error('transport failure'); });
  assert.deepEqual(await f.core.send(event), { status: 'uncertain' });
  let finish;
  const late = new BridgeCore(f.store, { ...f.options, send: () => new Promise(resolve => { finish = resolve; }) });
  assert.deepEqual(await late.send({ ...event, event_id: 'late' }), { status: 'uncertain' });
  finish({ key: { id: 'late-id' } });
  await new Promise(resolve => setImmediate(resolve));
  const restarted = new BridgeCore(new DurableStore(f.dir), { ...f.options, send: () => assert.fail('must not resend') });
  assert.deepEqual(await restarted.send(event), { status: 'uncertain' });
  assert.deepEqual(await restarted.send({ ...event, event_id: 'late' }), { status: 'uncertain' });
});

test('LID alternate PN accepted but oversized inbound and malformed event IDs rejected', async t => {
  const f = fixture(t);
  await f.core.ingest({ key: { id: 'alt-1', remoteJid: '123@lid', remoteJidAlt: `${phone}@s.whatsapp.net` }, message: { conversation: 'hello' } }, 'notify');
  await f.core.ingest({ key: { id: 'long-1', remoteJid: `${phone}@s.whatsapp.net` }, message: { conversation: 'a'.repeat(8001) } }, 'notify');
  assert.equal(f.core.inbox().length, 1);
  await assert.rejects(f.core.send({ ...event, event_id: '__proto__' }), { statusCode: 400 });
  await assert.rejects(f.core.send({ ...event, event_id: '../escape' }), { statusCode: 400 });
});

test('quoted transport ID persists verbatim for backend correlation after restart', async t => {
  const f = fixture(t);
  await f.core.ingest({
    key: { id: 'quote-1', remoteJid: `${phone}@s.whatsapp.net` },
    message: { ephemeralMessage: { message: { extendedTextMessage: {
      text: 'available 5', contextInfo: { stanzaId: 'original-outbound-wa-id' },
    } } } },
  }, 'notify');
  await f.core.ingest({
    key: { id: 'quote-unknown', remoteJid: `${phone}@s.whatsapp.net` },
    message: { extendedTextMessage: { text: 'unknown reference', contextInfo: { stanzaId: 'unknown-outbound-id' } } },
  }, 'notify');
  const rows = new BridgeCore(new DurableStore(f.dir), f.options).inbox();
  assert.equal(rows[0].quoted_transport_id, 'original-outbound-wa-id');
  assert.equal(rows[1].quoted_transport_id, 'unknown-outbound-id');
});
