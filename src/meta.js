import { createHmac, timingSafeEqual } from 'node:crypto';

// Meta signs every webhook POST with HMAC-SHA256 of the raw body using the app secret.
export function isValidSignature(rawBody, signatureHeader, appSecret) {
  if (!appSecret || !signatureHeader || !signatureHeader.startsWith('sha256=')) return false;
  const expected = createHmac('sha256', appSecret).update(rawBody).digest('hex');
  const received = signatureHeader.slice('sha256='.length);
  if (received.length !== expected.length) return false;
  return timingSafeEqual(Buffer.from(received, 'hex'), Buffer.from(expected, 'hex'));
}

// Pulls every leadgen event out of a webhook payload. One POST can batch several.
export function extractLeadEvents(payload) {
  if (!payload || payload.object !== 'page' || !Array.isArray(payload.entry)) return [];
  const events = [];
  for (const entry of payload.entry) {
    for (const change of entry.changes || []) {
      if (change.field !== 'leadgen' || !change.value?.leadgen_id) continue;
      events.push({
        leadgenId: String(change.value.leadgen_id),
        pageId: String(change.value.page_id || entry.id || ''),
        formId: change.value.form_id ? String(change.value.form_id) : '',
        adId: change.value.ad_id ? String(change.value.ad_id) : '',
        createdTime: change.value.created_time,
      });
    }
  }
  return events;
}

async function graphGet(path, fields, { pageAccessToken, graphVersion }, fetchImpl) {
  const url = new URL(`https://graph.facebook.com/${graphVersion}/${path}`);
  url.searchParams.set('fields', fields);
  url.searchParams.set('access_token', pageAccessToken);
  const res = await fetchImpl(url);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(`Graph API ${path} failed (${res.status}): ${body?.error?.message || 'unknown error'}`);
  }
  return body;
}

// Fetches the lead's answers plus campaign/ad context. The form name is a
// nice-to-have, so a failure there doesn't block the alert.
export async function fetchLead(leadgenId, metaConfig, fetchImpl = fetch) {
  const lead = await graphGet(
    leadgenId,
    'id,created_time,field_data,ad_id,ad_name,adset_name,campaign_name,form_id,platform,is_organic',
    metaConfig,
    fetchImpl,
  );
  if (lead.form_id) {
    try {
      const form = await graphGet(lead.form_id, 'name', metaConfig, fetchImpl);
      lead.form_name = form.name;
    } catch {
      // ignore – form name is optional
    }
  }
  return lead;
}
