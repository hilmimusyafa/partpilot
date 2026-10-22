import { mkdirSync, chmodSync, existsSync, readFileSync, openSync, writeFileSync, fsyncSync, closeSync, renameSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { createHash, randomUUID } from 'node:crypto';

export function failure(statusCode, message) { return Object.assign(new Error(message), { statusCode }); }
export function privateDirectory(dir) { mkdirSync(dir, { recursive: true, mode: 0o700 }); chmodSync(dir, 0o700); }

// One process owns the volume. The HTTP listener is acquired before opening it.
// A completed rename is the commit point; fsync also makes the directory entry durable on Linux.
export function atomicWrite(path, value, replacer) {
  privateDirectory(dirname(path));
  const temp = `${path}.${randomUUID()}.tmp`;
  const fd = openSync(temp, 'wx', 0o600);
  try { writeFileSync(fd, JSON.stringify(value, replacer)); fsyncSync(fd); } finally { closeSync(fd); }
  renameSync(temp, path);
  chmodSync(path, 0o600);
  if (process.platform !== 'win32') {
    const directory = openSync(dirname(path), 'r');
    try { fsyncSync(directory); } finally { closeSync(directory); }
  }
}

export class DurableStore {
  constructor(dir) {
    privateDirectory(dir);
    this.path = join(dir, 'ledger.json');
    this.state = existsSync(this.path) ? JSON.parse(readFileSync(this.path, 'utf8')) : { version: 1, outbox: {}, inbox: {}, seen: {} };
    if (this.state.version !== 1 || !this.state.outbox || !this.state.inbox || !this.state.seen) throw new Error('invalid_state');
    for (const item of Object.values(this.state.outbox)) if (item.status === 'pending') item.status = 'uncertain';
    this.save();
  }
  save() { atomicWrite(this.path, this.state); }
}

export function validPhone(phone) { return typeof phone === 'string' && /^[1-9]\d{7,14}$/.test(phone); }
function phoneFromJid(jid) {
  if (typeof jid !== 'string') return undefined;
  const match = /^(\d+)(?::\d+)?@s\.whatsapp\.net$/.exec(jid);
  return match && validPhone(match[1]) ? match[1] : undefined;
}
function response(item) { return item.message_id ? { status: item.status, message_id: item.message_id } : { status: item.status }; }

export class BridgeCore {
  constructor(store, { enabled, recipients, connected, send, timeoutMs = 15000 }) {
    this.store = store; this.enabled = enabled; this.recipients = new Set(recipients);
    this.connected = connected; this.transportSend = send; this.timeoutMs = timeoutMs;
  }
  checkPhone(phone) {
    if (!validPhone(phone)) throw failure(400, 'invalid_phone');
    if (!this.recipients.has(phone)) throw failure(403, 'recipient_not_allowed');
  }
  async send({ event_id, phone, text } = {}) {
    if (!this.enabled) throw failure(503, 'whatsapp_disabled');
    this.checkPhone(phone);
    if (typeof event_id !== 'string' || !/^[a-zA-Z0-9_-]{1,128}$/.test(event_id) || ['__proto__', 'constructor', 'prototype'].includes(event_id)) throw failure(400, 'invalid_event_id');
    if (typeof text !== 'string' || !text.trim() || text.length > 8000) throw failure(400, 'invalid_text');
    const fingerprint = createHash('sha256').update(JSON.stringify([phone, text])).digest('hex');
    const existing = Object.hasOwn(this.store.state.outbox, event_id) ? this.store.state.outbox[event_id] : undefined;
    if (existing) {
      if (existing.fingerprint !== fingerprint) throw failure(409, 'event_payload_mismatch');
      return response(existing);
    }
    if (!this.connected()) return { status: 'pending' };
    const item = { fingerprint, status: 'pending', created_at: new Date().toISOString() };
    this.store.state.outbox[event_id] = item;
    this.store.save(); // MUST complete before any external send is attempted.
    let timer;
    try {
      const sent = await Promise.race([
        this.transportSend(`${phone}@s.whatsapp.net`, text),
        new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('send_timeout')), this.timeoutMs); }),
      ]);
      if (!sent?.key?.id) throw new Error('missing_message_id');
      item.status = 'sent'; item.message_id = sent.key.id;
    } catch { item.status = 'uncertain'; }
    finally { clearTimeout(timer); }
    this.store.save();
    return response(item);
  }
  async ingest(message, type, resolveLid = async () => undefined) {
    if (!this.enabled || type !== 'notify' || message?.key?.fromMe || !message?.key?.id) return;
    const jid = message.key.remoteJid;
    if (typeof jid !== 'string' || (!jid.endsWith('@s.whatsapp.net') && !jid.endsWith('@lid'))) return;
    let phone = phoneFromJid(jid);
    if (!phone && jid.endsWith('@lid')) {
      phone = phoneFromJid(message.key.remoteJidAlt);
      if (!phone) phone = phoneFromJid(await resolveLid(jid));
    }
    if (!this.recipients.has(phone)) return;
    let content = message.message;
    for (let i = 0; i < 4; i++) {
      const wrapped = content?.ephemeralMessage?.message;
      if (!wrapped) break;
      content = wrapped;
    }
    const text = content?.conversation ?? content?.extendedTextMessage?.text;
    if (typeof text !== 'string' || !text.trim() || text.length > 8000) return;
    const quote = content?.extendedTextMessage?.contextInfo?.stanzaId;
    // Preserve unknown IDs for the database to reject; never downgrade a malformed
    // explicit quote to an unquoted reply that might match the current run.
    if (quote != null && (typeof quote !== 'string' || !quote.length || quote.length > 1024)) return;
    // Include sender in identity to avoid one contact suppressing another's message ID.
    const id = createHash('sha256').update(`${phone}:${message.key.id}`).digest('hex');
    if (Object.hasOwn(this.store.state.seen, id)) return;
    let timestamp = Number(message.messageTimestamp);
    if (!Number.isFinite(timestamp) || timestamp < 0 || timestamp > 8640000000000) timestamp = Date.now() / 1000;
    const item = { message_id: id, phone, text, received_at: new Date(timestamp * 1000).toISOString(), quoted_transport_id: quote ?? null };
    this.store.state.inbox[id] = item;
    this.store.state.seen[id] = true;
    this.store.save();
  }
  inbox() { return Object.values(this.store.state.inbox).slice(0, 100); }
  ack(ids) {
    if (!Array.isArray(ids) || ids.length > 100 || ids.some(id => typeof id !== 'string' || !/^[a-f0-9]{64}$/.test(id))) throw failure(400, 'invalid_message_ids');
    for (const id of ids) delete this.store.state.inbox[id];
    this.store.save();
  }
}
