import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import makeWASocket, { initAuthCreds, BufferJSON, proto, DisconnectReason, Browsers } from 'baileys';
import pino from 'pino';
import QRCode from 'qrcode';
import { atomicWrite, failure } from './core.js';

export function privateAuth(dir) {
  const path = join(dir, 'auth.json');
  const data = existsSync(path) ? JSON.parse(readFileSync(path, 'utf8'), BufferJSON.reviver) : { creds: initAuthCreds(), keys: {} };
  if (!data.creds || !data.keys) throw new Error('invalid_auth_state');
  const persist = () => atomicWrite(path, data, BufferJSON.replacer);
  return {
    state: {
      creds: data.creds,
      keys: {
        get: async (type, ids) => {
          const result = {};
          for (const id of ids) {
            let value = data.keys[type]?.[id];
            if (type === 'app-state-sync-key' && value) value = proto.Message.AppStateSyncKeyData.create(value);
            result[id] = value;
          }
          return result;
        },
        set: async updates => {
          for (const [type, entries] of Object.entries(updates)) {
            if (!Object.hasOwn(data.keys, type)) data.keys[type] = {};
            for (const [id, value] of Object.entries(entries)) {
              if (value == null) delete data.keys[type][id];
              else Object.defineProperty(data.keys[type], id, { value, writable: true, enumerable: true, configurable: true });
            }
          }
          persist();
        },
      },
    },
    saveCreds: async () => persist(),
    reset: () => { data.creds = initAuthCreds(); data.keys = {}; persist(); },
  };
}

export class WhatsAppTransport {
  constructor({ enabled, dir, onMessage, onFatal = () => {}, socketFactory = makeWASocket }) {
    this.enabled = enabled; this.dir = dir; this.onMessage = onMessage; this.onFatal = onFatal;
    this.socketFactory = socketFactory; this.connection = enabled ? 'disconnected' : 'disabled';
    this.qr = null; this.socket = null; this.attempts = 0; this.stopped = false;
  }
  status() { return { connection: this.connection, qr_data_url: this.qr, enabled: this.enabled }; }
  async restore() {
    if (this.enabled && existsSync(join(this.dir, 'auth.json')) && privateAuth(this.dir).state.creds.registered) await this.connect();
  }
  async connect() {
    if (!this.enabled) throw failure(503, 'whatsapp_disabled');
    if (this.socket) return;
    clearTimeout(this.reconnectTimer); this.stopped = false;
    this.connection = 'connecting'; this.qr = null;
    const auth = privateAuth(this.dir);
    const socket = this.socketFactory({
      auth: auth.state,
      logger: pino({ level: 'silent' }),
      browser: Browsers.ubuntu('PartPilot'),
      syncFullHistory: false,
      shouldSyncHistoryMessage: () => false,
      shouldIgnoreJid: jid => jid.endsWith('@g.us') || jid.endsWith('@broadcast') || jid.endsWith('@newsletter'),
      markOnlineOnConnect: false,
      emitOwnEvents: false,
      enableAutoSessionRecreation: false,
      enableRecentMessageCache: false,
      maxMsgRetryCount: 0,
      getMessage: async () => undefined,
      connectTimeoutMs: 20000,
      defaultQueryTimeoutMs: 15000,
      qrTimeout: 60000,
    });
    this.socket = socket;
    const guard = fn => (...args) => { Promise.resolve().then(() => fn(...args)).catch(() => {
      this.stop(); this.connection = 'error'; this.onFatal();
    }); };
    socket.ev.on('creds.update', guard(async () => { if (this.socket === socket) await auth.saveCreds(); }));
    socket.ev.on('messages.upsert', guard(async ({ messages, type }) => {
      if (this.socket !== socket || type !== 'notify') return;
      for (const message of messages) await this.onMessage(message, type, lid => socket.signalRepository.lidMapping.getPNForLID(lid));
    }));
    socket.ev.on('connection.update', guard(async ({ connection, qr, lastDisconnect }) => {
      if (this.socket !== socket) return;
      if (qr) {
        this.connection = 'qr';
        const serial = Symbol(); this.qrSerial = serial;
        const image = await QRCode.toDataURL(qr, { errorCorrectionLevel: 'M', margin: 2, width: 320 });
        if (this.socket === socket && this.qrSerial === serial && this.connection === 'qr') this.qr = image;
      }
      if (connection === 'open') { this.connection = 'connected'; this.qr = null; this.attempts = 0; }
      if (connection === 'close') {
        this.qr = null; this.qrSerial = null; this.socket = null;
        const status = lastDisconnect?.error?.output?.statusCode;
        if (status === DisconnectReason.loggedOut || status === DisconnectReason.badSession) {
          this.connection = 'logged_out'; auth.reset(); return;
        }
        this.connection = 'disconnected';
        if (!this.stopped && (auth.state.creds.registered || status === DisconnectReason.restartRequired)) {
          const delay = Math.min(30000, 1000 * (2 ** Math.min(this.attempts++, 5)));
          this.reconnectTimer = setTimeout(() => { this.connect().catch(() => { this.connection = 'error'; }); }, delay);
        }
      }
    }));
  }
  async check(phone) {
    if (!this.enabled || this.connection !== 'connected') throw failure(503, 'whatsapp_not_connected');
    const results = await this.socket.onWhatsApp(`${phone}@s.whatsapp.net`);
    const found = results?.find(item => item.exists);
    return { registered: Boolean(found), jid: found?.jid ?? null };
  }
  send(jid, text) {
    if (!this.enabled || this.connection !== 'connected') throw failure(503, 'whatsapp_not_connected');
    return this.socket.sendMessage(jid, { text, linkPreview: null });
  }
  stop() {
    this.stopped = true; clearTimeout(this.reconnectTimer); this.qr = null;
    const socket = this.socket; this.socket = null;
    socket?.end(new Error('bridge_stopped'));
    this.connection = this.enabled ? 'disconnected' : 'disabled';
  }
}
