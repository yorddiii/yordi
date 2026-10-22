import { enabledChannels } from './config.js';
import { renderText, renderEmail } from './format.js';

async function expectOk(res, label) {
  if (res.ok) return;
  const body = await res.text().catch(() => '');
  throw new Error(`${label} failed (${res.status}): ${body.slice(0, 300)}`);
}

// Twilio rejects bodies over 1600 characters.
const SMS_MAX = 1500;

export async function sendSms(text, { accountSid, authToken, from, to }, fetchImpl = fetch) {
  const body = text.length > SMS_MAX ? `${text.slice(0, SMS_MAX - 1)}…` : text;
  const auth = Buffer.from(`${accountSid}:${authToken}`).toString('base64');
  await Promise.all(
    to.map(async (recipient) => {
      const res = await fetchImpl(`https://api.twilio.com/2010-04-01/Accounts/${accountSid}/Messages.json`, {
        method: 'POST',
        headers: { Authorization: `Basic ${auth}`, 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ To: recipient, From: from, Body: body }),
      });
      await expectOk(res, `SMS to ${recipient}`);
    }),
  );
}

export async function sendEmail({ subject, text, html }, { apiKey, from, to }, fetchImpl = fetch) {
  const res = await fetchImpl('https://api.resend.com/emails', {
    method: 'POST',
    headers: { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ from, to, subject, text, html }),
  });
  await expectOk(res, 'Email');
}

export async function sendTelegram(text, { botToken, chatIds }, fetchImpl = fetch) {
  await Promise.all(
    chatIds.map(async (chatId) => {
      const res = await fetchImpl(`https://api.telegram.org/bot${botToken}/sendMessage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chat_id: chatId, text, disable_web_page_preview: true }),
      });
      await expectOk(res, `Telegram to ${chatId}`);
    }),
  );
}

// Sends the alert on every configured channel at once. One channel failing
// never stops the others; the result lists what went out and what didn't.
export async function notifyAll(summary, config, fetchImpl = fetch) {
  const text = renderText(summary, config.businessName);
  const senders = {
    sms: () => sendSms(text, config.sms, fetchImpl),
    email: () => sendEmail(renderEmail(summary, config.businessName), config.email, fetchImpl),
    telegram: () => sendTelegram(text, config.telegram, fetchImpl),
  };
  const channels = enabledChannels(config);
  const results = await Promise.allSettled(channels.map((channel) => senders[channel]()));
  return channels.map((channel, i) => ({
    channel,
    ok: results[i].status === 'fulfilled',
    error: results[i].status === 'rejected' ? results[i].reason.message : undefined,
  }));
}
