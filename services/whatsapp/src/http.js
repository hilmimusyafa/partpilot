import { timingSafeEqual } from 'node:crypto';
import { failure } from './core.js';

async function body(req) {
  if (!req.headers['content-type']?.startsWith('application/json')) throw failure(415, 'json_required');
  const chunks = []; let size = 0;
  for await (const chunk of req) {
    size += chunk.length;
    if (size > 65536) throw failure(413, 'body_too_large');
    chunks.push(chunk);
  }
  try {
    const value = JSON.parse(Buffer.concat(chunks).toString('utf8'));
    if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error();
    return value;
  } catch { throw failure(400, 'invalid_json'); }
}

export function createHandler({ token, transport, core }) {
  if (typeof token !== 'string' || token.length < 32) throw new Error('internal_token_too_short');
  const expected = Buffer.from(`Bearer ${token}`);
  return async (req, res) => {
    res.setHeader('Content-Type', 'application/json; charset=utf-8');
    res.setHeader('Cache-Control', 'no-store');
    res.setHeader('X-Content-Type-Options', 'nosniff');
    try {
      const supplied = Buffer.from(req.headers.authorization ?? '');
      if (supplied.length !== expected.length || !timingSafeEqual(supplied, expected)) throw failure(401, 'unauthorized');
      const pathname = new URL(req.url, 'http://localhost').pathname;
      let result;
      if (req.method === 'GET' && pathname === '/status') result = transport.status();
      else if (req.method === 'GET' && pathname === '/inbox') result = { messages: core.inbox() };
      else if (req.method === 'POST' && pathname === '/connect') { await body(req); await transport.connect(); result = transport.status(); }
      else if (req.method === 'POST' && pathname === '/check') {
        const { phone } = await body(req); core.checkPhone(phone); result = await transport.check(phone);
      }
      else if (req.method === 'POST' && pathname === '/send') result = await core.send(await body(req));
      else if (req.method === 'POST' && pathname === '/inbox/ack') { const { message_ids } = await body(req); core.ack(message_ids); result = { acknowledged: true }; }
      else throw failure(404, 'not_found');
      res.end(JSON.stringify(result));
    } catch (error) {
      res.statusCode = error.statusCode ?? 500;
      res.end(JSON.stringify({ error: error.statusCode ? error.message : 'internal_error' }));
    }
  };
}
