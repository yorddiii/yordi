const CONTACT_FIELDS = new Set(['full_name', 'first_name', 'last_name', 'phone_number', 'email']);

const PLATFORM_LABELS = { fb: 'Facebook', ig: 'Instagram', msg: 'Messenger', wa: 'WhatsApp' };

// "what_type_of_vehicle_do_you_have?" -> "What type of vehicle do you have?"
export function humanizeFieldName(name) {
  const text = String(name).replace(/_/g, ' ').replace(/\s+/g, ' ').trim();
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function humanizeValue(value) {
  return String(value).replace(/_/g, ' ').trim();
}

export function leadsCenterUrl(pageId) {
  return `https://business.facebook.com/latest/leads_center?asset_id=${encodeURIComponent(pageId)}`;
}

// Turns a Graph API lead object (or null if it couldn't be fetched) into a
// flat summary the notification channels can render.
export function summarizeLead(lead, { pageId, timezone }) {
  const fields = {};
  for (const field of lead?.field_data || []) {
    fields[field.name] = (field.values || []).filter((v) => v !== '' && v != null);
  }
  const first = (key) => fields[key]?.[0] || '';

  const name = first('full_name') || [first('first_name'), first('last_name')].filter(Boolean).join(' ');
  const phone = first('phone_number');
  const email = first('email');

  const answers = Object.entries(fields)
    .filter(([key, values]) => !CONTACT_FIELDS.has(key) && values.length)
    .map(([key, values]) => ({ label: humanizeFieldName(key), value: values.map(humanizeValue).join(', ') }));

  const created = lead?.created_time ? new Date(lead.created_time) : new Date();
  const receivedAt = created.toLocaleString('en-US', {
    timeZone: timezone,
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });

  return {
    fetched: Boolean(lead),
    id: lead?.id || '',
    name: name || 'Unknown name',
    phone,
    phoneHref: phone ? `tel:${phone.replace(/[^\d+]/g, '')}` : '',
    email,
    answers,
    formName: lead?.form_name || '',
    campaignName: lead?.campaign_name || '',
    adName: lead?.ad_name || '',
    platform: PLATFORM_LABELS[lead?.platform] || '',
    isOrganic: Boolean(lead?.is_organic),
    receivedAt,
    leadsCenterUrl: leadsCenterUrl(pageId),
  };
}

// Plain-text version used for SMS and Telegram. Kept short so it reads well
// on a lock screen: who, how to reach them, what they want, then the source.
export function renderText(summary, businessName) {
  if (!summary.fetched) {
    return [
      `🚨 NEW LEAD – ${businessName}`,
      'Someone just filled out your Meta form, but the details could not be loaded automatically.',
      `Open Leads Center now: ${summary.leadsCenterUrl}`,
    ].join('\n');
  }

  const lines = [`🚨 NEW LEAD – ${businessName}`, '', `👤 ${summary.name}`];
  if (summary.phone) lines.push(`📞 ${summary.phone}`);
  if (summary.email) lines.push(`✉️ ${summary.email}`);
  if (summary.answers.length) {
    lines.push('');
    for (const { label, value } of summary.answers) lines.push(`• ${label}${/[?:]$/.test(label) ? '' : ':'} ${value}`);
  }
  lines.push('');
  const source = [summary.platform, summary.formName && `form "${summary.formName}"`].filter(Boolean).join(' · ');
  if (source) lines.push(`Source: ${source}`);
  if (summary.adName) lines.push(`Ad: ${summary.adName}`);
  lines.push(`Received: ${summary.receivedAt}`);
  lines.push('');
  lines.push(summary.phone ? '⏱ Call or text them now – speed wins the job!' : '⏱ Reach out now – speed wins the job!');
  return lines.join('\n');
}

const escapeHtml = (s) =>
  String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);

export function renderEmail(summary, businessName) {
  const subject = summary.fetched
    ? `🚨 New lead: ${summary.name}${summary.phone ? ` – ${summary.phone}` : ''}`
    : `🚨 New lead for ${businessName} – open Leads Center`;
  const text = renderText(summary, businessName);

  const row = (label, value) =>
    `<tr><td style="padding:6px 12px 6px 0;color:#6b7280;vertical-align:top">${escapeHtml(label)}</td>` +
    `<td style="padding:6px 0;font-weight:600">${value}</td></tr>`;

  const rows = [];
  if (summary.fetched) {
    rows.push(row('Name', escapeHtml(summary.name)));
    if (summary.phone) rows.push(row('Phone', `<a href="${escapeHtml(summary.phoneHref)}">${escapeHtml(summary.phone)}</a>`));
    if (summary.email) rows.push(row('Email', `<a href="mailto:${escapeHtml(summary.email)}">${escapeHtml(summary.email)}</a>`));
    for (const { label, value } of summary.answers) rows.push(row(label, escapeHtml(value)));
    if (summary.platform) rows.push(row('Platform', escapeHtml(summary.platform)));
    if (summary.formName) rows.push(row('Form', escapeHtml(summary.formName)));
    if (summary.campaignName) rows.push(row('Campaign', escapeHtml(summary.campaignName)));
    if (summary.adName) rows.push(row('Ad', escapeHtml(summary.adName)));
    rows.push(row('Received', escapeHtml(summary.receivedAt)));
  }

  const button = (href, label, color) =>
    `<a href="${escapeHtml(href)}" style="display:inline-block;margin:4px 8px 4px 0;padding:12px 20px;border-radius:8px;` +
    `background:${color};color:#fff;text-decoration:none;font-weight:600">${escapeHtml(label)}</a>`;

  const buttons = [];
  if (summary.phoneHref) buttons.push(button(summary.phoneHref, 'Call now', '#16a34a'));
  if (summary.phone) buttons.push(button(summary.phoneHref.replace('tel:', 'sms:'), 'Text now', '#2563eb'));
  buttons.push(button(summary.leadsCenterUrl, 'Open Leads Center', '#374151'));

  const html = `<!doctype html><html><body style="font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#111827;margin:0;padding:24px;background:#f9fafb">
<div style="max-width:520px;margin:0 auto;background:#fff;border-radius:12px;padding:24px;border:1px solid #e5e7eb">
<h2 style="margin:0 0 4px">🚨 New lead – ${escapeHtml(businessName)}</h2>
<p style="margin:0 0 16px;color:#b91c1c;font-weight:600">Respond now – leads contacted within 5 minutes are far more likely to book.</p>
${summary.fetched ? `<table style="border-collapse:collapse;width:100%;margin-bottom:16px">${rows.join('')}</table>` : '<p>Someone just filled out your Meta form, but the details could not be loaded automatically. Open Leads Center to see them.</p>'}
<div>${buttons.join('')}</div>
</div></body></html>`;

  return { subject, text, html };
}
