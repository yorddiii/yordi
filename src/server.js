import { createServer } from 'node:http';
import { fileURLToPath } from 'node:url';
import { loadDotEnv, getConfig, enabledChannels } from './config.js';
import { isValidSignature, extractLeadEvents } from './meta.js';
import { handleLeadEvent } from './handler.js';

const MAX_BODY_BYTES = 1024 * 1024;

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    req.on('data', (chunk) => {
      size += chunk.length;
      if (size > MAX_BODY_BYTES) {
        reject(new Error('body too large'));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on('end', () => resolve(Buffer.concat(chunks)));
    req.on('error', reject);
  });
}

function send(res, status, body = '', type = 'text/plain') {
  res.writeHead(status, { 'Content-Type': type });
  res.end(body);
}

export function createApp(config, { fetchImpl = fetch, log = console } = {}) {
  return createServer(async (req, res) => {
    const url = new URL(req.url, 'http://localhost');

    if (req.method === 'GET' && url.pathname === '/') {
      return send(res, 200, JSON.stringify({ ok: true, channels: enabledChannels(config) }), 'application/json');
    }

    if (url.pathname !== '/webhook') return send(res, 404, 'Not found');

    // Meta's one-time subscription handshake.
    if (req.method === 'GET') {
      const mode = url.searchParams.get('hub.mode');
      const token = url.searchParams.get('hub.verify_token');
      const challenge = url.searchParams.get('hub.challenge');
      if (mode === 'subscribe' && config.meta.verifyToken && token === config.meta.verifyToken) {
        log.info('Webhook verified by Meta');
        return send(res, 200, challenge || '');
      }
      return send(res, 403, 'Verification failed');
    }

    if (req.method !== 'POST') return send(res, 405, 'Method not allowed');

    let raw;
    try {
      raw = await readBody(req);
    } catch {
      return send(res, 413, 'Payload too large');
    }

    if (!isValidSignature(raw, req.headers['x-hub-signature-256'], config.meta.appSecret)) {
      log.warn('Rejected webhook with missing or invalid signature');
      return send(res, 401, 'Invalid signature');
    }

    let payload;
    try {
      payload = JSON.parse(raw.toString('utf8'));
    } catch {
      return send(res, 400, 'Invalid JSON');
    }

    // Acknowledge right away so Meta doesn't retry, then do the slow work.
    send(res, 200, 'EVENT_RECEIVED');

    for (const event of extractLeadEvents(payload)) {
      log.info(`[lead ${event.leadgenId}] received (form ${event.formId || '?'})`);
      handleLeadEvent(event, config, { fetchImpl, log }).catch((err) =>
        log.error(`[lead ${event.leadgenId}] unexpected error: ${err.stack || err.message}`),
      );
    }
  });
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  loadDotEnv();
  const config = getConfig();
  const missing = ['verifyToken', 'appSecret', 'pageAccessToken'].filter((k) => !config.meta[k]);
  if (missing.length) console.warn(`⚠️  Missing Meta settings: ${missing.join(', ')} – see .env.example`);
  const channels = enabledChannels(config);
  if (!channels.length) console.warn('⚠️  No notification channel configured – alerts will not be delivered.');
  createApp(config).listen(config.port, () => {
    console.log(`Lead alerts listening on :${config.port} (channels: ${channels.join(', ') || 'none'})`);
  });
}
