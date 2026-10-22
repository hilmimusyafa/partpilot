import { createServer } from 'node:http';
import { resolve } from 'node:path';
import { BridgeCore, DurableStore, validPhone } from './core.js';
import { createHandler } from './http.js';

// libsignal has direct console calls in addition to the Baileys logger. Suppress
// dependency output completely; operational messages below are fixed strings only.
for (const method of ['log', 'info', 'warn', 'error', 'debug', 'trace', 'dir']) console[method] = () => {};
process.umask(0o077);
const { WhatsAppTransport } = await import('./transport.js');

const token = process.env.PARTPILOT_WA_INTERNAL_TOKEN;
const enabled = process.env.PARTPILOT_WA_ENABLED === 'true';
const recipients = (process.env.PARTPILOT_WA_RECIPIENTS ?? '').split(',').map(x => x.trim()).filter(Boolean);
if (!token || token.length < 32 || recipients.some(phone => !validPhone(phone))) {
  process.stderr.write('WhatsApp bridge configuration invalid.\n'); process.exit(1);
}
let handler = (_, res) => { res.writeHead(503); res.end(); };
const server = createServer((req, res) => handler(req, res));
server.requestTimeout = 20000; server.headersTimeout = 10000;
let transport;
function shutdown(code) { transport?.stop(); server.close(() => process.exit(code)); setTimeout(() => process.exit(code), 3000).unref(); }
process.on('SIGTERM', () => shutdown(0)); process.on('SIGINT', () => shutdown(0));
process.on('uncaughtException', () => { process.stderr.write('WhatsApp bridge stopped after internal failure.\n'); shutdown(1); });
process.on('unhandledRejection', () => { process.stderr.write('WhatsApp bridge stopped after internal failure.\n'); shutdown(1); });
server.on('error', () => { process.stderr.write('WhatsApp bridge could not bind private port.\n'); process.exit(1); });
// Bind before loading the state: the fixed localhost port enforces one live process.
server.listen(18081, '127.0.0.1', async () => {
  try {
    const dir = resolve(process.env.PARTPILOT_WA_STATE_DIR ?? './state');
    const store = new DurableStore(dir);
    let core;
    transport = new WhatsAppTransport({ enabled, dir, onMessage: (...args) => core.ingest(...args), onFatal: () => shutdown(1) });
    core = new BridgeCore(store, { enabled, recipients, connected: () => transport.connection === 'connected', send: (jid, text) => transport.send(jid, text) });
    handler = createHandler({ token, transport, core });
    await transport.restore();
    process.stdout.write('WhatsApp bridge ready on private loopback.\n');
  } catch { process.stderr.write('WhatsApp bridge state initialization failed.\n'); shutdown(1); }
});
