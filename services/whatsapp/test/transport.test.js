import test from 'node:test';
import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import { mkdtempSync, rmSync } from 'node:fs';
import { join } from 'node:path';
import { WhatsAppTransport, privateAuth } from '../src/transport.js';

function fixture(t) {
  const dir = mkdtempSync(join(process.cwd(), '.test-state-'));
  t.after(() => rmSync(dir, { recursive: true, force: true }));
  return dir;
}

test('paired QR identity restores and reconnects even when registered is false', async t => {
  const dir = fixture(t);
  const auth = privateAuth(dir);
  auth.state.creds.registered = false;
  auth.state.creds.me = { id: '12025550123:1@s.whatsapp.net', name: 'Test' };
  await auth.saveCreds();
  const sockets = [];
  const transport = new WhatsAppTransport({ enabled: true, dir, onMessage: async () => {}, socketFactory: () => {
    const socket = { ev: new EventEmitter(), end: () => {} };
    sockets.push(socket); return socket;
  } });
  t.after(() => transport.stop());
  await transport.restore();
  assert.equal(sockets.length, 1);
  sockets[0].ev.emit('connection.update', { connection: 'close', lastDisconnect: { error: { output: { statusCode: 408 } } } });
  await new Promise(resolve => setTimeout(resolve, 1150));
  assert.equal(sockets.length, 2);
  sockets[1].ev.emit('connection.update', { connection: 'close', lastDisconnect: { error: { output: { statusCode: 401 } } } });
  await new Promise(resolve => setTimeout(resolve, 20));
  assert.equal(transport.connection, 'logged_out');
  assert.equal(privateAuth(dir).state.creds.me, undefined);
});
test('auth credentials, binary keys and LID maps round trip durably', async t => {
  const dir = fixture(t);
  const auth = privateAuth(dir);
  auth.state.creds.registered = true;
  await auth.saveCreds();
  await auth.state.keys.set({ session: { example: Buffer.from([1, 2, 3]) }, 'lid-mapping': { example: '12025550123' }, 'app-state-sync-key': { example: { keyData: Buffer.from([4, 5]) } } });
  const reloaded = privateAuth(dir);
  assert.equal(reloaded.state.creds.registered, true);
  assert.deepEqual((await reloaded.state.keys.get('session', ['example'])).example, Buffer.from([1, 2, 3]));
  assert.equal((await reloaded.state.keys.get('lid-mapping', ['example'])).example, '12025550123');
  assert.deepEqual((await reloaded.state.keys.get('app-state-sync-key', ['example'])).example.keyData, Buffer.from([4, 5]));
  await reloaded.state.keys.set({ session: { example: null } });
  assert.equal((await privateAuth(dir).state.keys.get('session', ['example'])).example, undefined);
});
test('new session waits for explicit connect; reconnect is idempotent and QR clears on disconnect', async t => {
  const dir = fixture(t);
  const sockets = [];
  const transport = new WhatsAppTransport({ enabled: true, dir, onMessage: async () => {}, socketFactory: options => {
    assert.equal(options.syncFullHistory, false);
    assert.equal(options.shouldSyncHistoryMessage({}), false);
    assert.equal(options.enableRecentMessageCache, false);
    const socket = { ev: new EventEmitter(), end: () => {}, signalRepository: { lidMapping: { getPNForLID: async () => null } } };
    sockets.push(socket); return socket;
  } });
  t.after(() => transport.stop());
  await transport.restore();
  assert.equal(sockets.length, 0);
  await transport.connect(); await transport.connect();
  assert.equal(sockets.length, 1);
  sockets[0].ev.emit('connection.update', { qr: 'private-test-qr' });
  for (let attempt = 0; attempt < 100 && !transport.status().qr_data_url; attempt++) {
    await new Promise(resolve => setTimeout(resolve, 20));
  }
  assert.match(transport.status().qr_data_url, /^data:image\/png;base64,/);
  sockets[0].ev.emit('connection.update', { connection: 'close', lastDisconnect: { error: { output: { statusCode: 401 } } } });
  await new Promise(resolve => setTimeout(resolve, 5));
  assert.equal(transport.status().qr_data_url, null);
  await transport.connect();
  assert.equal(sockets.length, 2);
});
