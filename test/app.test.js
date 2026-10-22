import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHmac } from 'node:crypto';
import { getConfig } from '../src/config.js';
import { isValidSignature, extractLeadEvents } from '../src/meta.js';
import { summarizeLead, renderText, renderEmail, humanizeFieldName } from '../src/format.js';
import { createApp } from '../src/server.js';

const SECRET = 'app-secret';
const sign = (body) => `sha256=${createHmac('sha256', SECRET).update(body).digest('hex')}`;

const config = getConfig({
  META_VERIFY_TOKEN: 'verify-me',
  META_APP_SECRET: SECRET,
  META_PAGE_ACCESS_TOKEN: 'page-token',
  TWILIO_ACCOUNT_SID: 'AC123',
  TWILIO_AUTH_TOKEN: 'tw-token',
  TWILIO_FROM_NUMBER: '+15710000000',
  ALERT_SMS_TO: '+15711111111, +15712222222',
  RESEND_API_KEY: 're_123',
  ALERT_EMAIL_TO: 'owner@example.com',
});

const lead = {
  id: '999',
  created_time: '2026-10-22T18:05:00+0000',
  platform: 'ig',
  form_id: '42',
  ad_name: 'Fall Special',
  campaign_name: 'Leads – Oct',
  field_data: [
    { name: 'full_name', values: ['Jane Doe'] },
    { name: 'phone_number', values: ['+1 (571) 555-0199'] },
    { name: 'email', values: ['jane@example.com'] },
    { name: 'what_type_of_vehicle_do_you_have?', values: ['pickup_truck'] },
  ],
};

const leadPayload = (leadgenId) =>
  JSON.stringify({
    object: 'page',
    entry: [
      {
        id: '1146970505169606',
        time: 1,
        changes: [{ field: 'leadgen', value: { leadgen_id: leadgenId, page_id: '1146970505169606', form_id: '42' } }],
      },
    ],
  });

function mockFetch({ failGraph = false } = {}) {
  const calls = [];
  const impl = async (input, init = {}) => {
    const url = String(input);
    calls.push({ url, init });
    const json = (status, body) => new Response(JSON.stringify(body), { status });
    if (url.startsWith('https://graph.facebook.com/')) {
      if (failGraph) return json(400, { error: { message: 'token expired' } });
      if (url.includes('/42?')) return json(200, { name: 'Free Quote Form' });
      return json(200, lead);
    }
    return json(200, { ok: true });
  };
  return { impl, calls };
}

const silent = { info() {}, warn() {}, error() {} };

async function withServer(fetchImpl, fn) {
  const server = createApp(config, { fetchImpl, log: silent });
  await new Promise((r) => server.listen(0, r));
  const base = `http://127.0.0.1:${server.address().port}`;
  try {
    await fn(base);
  } finally {
    server.close();
  }
}

const waitFor = async (cond) => {
  for (let i = 0; i < 100 && !cond(); i++) await new Promise((r) => setTimeout(r, 10));
};

test('signature check accepts Meta-signed bodies only', () => {
  const body = Buffer.from('{"a":1}');
  assert.equal(isValidSignature(body, sign(body), SECRET), true);
  assert.equal(isValidSignature(body, sign(Buffer.from('{"a":2}')), SECRET), false);
  assert.equal(isValidSignature(body, undefined, SECRET), false);
  assert.equal(isValidSignature(body, 'sha256=abc', SECRET), false);
});

test('extracts leadgen events and ignores other fields', () => {
  const payload = JSON.parse(leadPayload('1'));
  payload.entry[0].changes.push({ field: 'feed', value: {} });
  assert.deepEqual(extractLeadEvents(payload).map((e) => e.leadgenId), ['1']);
  assert.deepEqual(extractLeadEvents({ object: 'user' }), []);
});

test('formats a readable alert', () => {
  const summary = summarizeLead({ ...lead, form_name: 'Free Quote Form' }, { pageId: 'P1', timezone: 'America/New_York' });
  assert.equal(humanizeFieldName('what_type_of_vehicle_do_you_have?'), 'What type of vehicle do you have?');
  assert.equal(summary.phoneHref, 'tel:+15715550199');
  const text = renderText(summary, 'Becris Detailer');
  assert.match(text, /Jane Doe/);
  assert.match(text, /\+1 \(571\) 555-0199/);
  assert.match(text, /What type of vehicle do you have\? pickup truck/);
  assert.match(text, /Instagram · form "Free Quote Form"/);
  assert.match(text, /Received: Thu, Oct 22, 2:05 PM/);
  const email = renderEmail({ ...summary, name: '<b>x</b>' }, 'Becris Detailer');
  assert.ok(!email.html.includes('<b>x</b>'));
});

test('webhook verification handshake', async () => {
  await withServer(mockFetch().impl, async (base) => {
    const ok = await fetch(`${base}/webhook?hub.mode=subscribe&hub.verify_token=verify-me&hub.challenge=123`);
    assert.equal(ok.status, 200);
    assert.equal(await ok.text(), '123');
    const bad = await fetch(`${base}/webhook?hub.mode=subscribe&hub.verify_token=nope&hub.challenge=123`);
    assert.equal(bad.status, 403);
  });
});

test('a new lead triggers SMS to every number plus email, once', async () => {
  const { impl, calls } = mockFetch();
  await withServer(impl, async (base) => {
    const body = leadPayload('lead-A');
    const post = () =>
      fetch(`${base}/webhook`, { method: 'POST', body, headers: { 'x-hub-signature-256': sign(body) } });

    assert.equal((await post()).status, 200);
    await waitFor(() => calls.filter((c) => !c.url.includes('graph.facebook.com')).length === 3);

    const sms = calls.filter((c) => c.url.includes('api.twilio.com'));
    assert.equal(sms.length, 2);
    assert.match(sms[0].init.body.get('Body'), /Jane Doe/);
    const email = calls.find((c) => c.url.includes('api.resend.com'));
    assert.match(JSON.parse(email.init.body).subject, /Jane Doe/);

    // Meta re-delivers the same event: no second round of alerts.
    assert.equal((await post()).status, 200);
    await new Promise((r) => setTimeout(r, 50));
    assert.equal(calls.filter((c) => c.url.includes('api.twilio.com')).length, 2);
  });
});

test('still alerts with a Leads Center link when lead details cannot be fetched', async () => {
  const { impl, calls } = mockFetch({ failGraph: true });
  await withServer(impl, async (base) => {
    const body = leadPayload('lead-B');
    await fetch(`${base}/webhook`, { method: 'POST', body, headers: { 'x-hub-signature-256': sign(body) } });
    await waitFor(() => calls.some((c) => c.url.includes('api.twilio.com')));
    const sms = calls.find((c) => c.url.includes('api.twilio.com'));
    assert.match(sms.init.body.get('Body'), /leads_center\?asset_id=1146970505169606/);
  });
});

test('rejects unsigned webhook posts', async () => {
  const { impl, calls } = mockFetch();
  await withServer(impl, async (base) => {
    const res = await fetch(`${base}/webhook`, { method: 'POST', body: leadPayload('lead-C') });
    assert.equal(res.status, 401);
    assert.equal(calls.length, 0);
  });
});
