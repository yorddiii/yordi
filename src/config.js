import { readFileSync, existsSync } from 'node:fs';

// Minimal .env loader so the app runs locally without extra dependencies.
// Values already set in the environment (e.g. on the host) take precedence.
export function loadDotEnv(path = '.env') {
  if (!existsSync(path)) return;
  for (const line of readFileSync(path, 'utf8').split(/\r?\n/)) {
    const match = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/i);
    if (!match) continue;
    const [, key, raw] = match;
    if (process.env[key] !== undefined) continue;
    process.env[key] = raw.replace(/^(['"])(.*)\1$/, '$2');
  }
}

const list = (value) =>
  (value || '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);

export function getConfig(env = process.env) {
  return {
    port: Number(env.PORT) || 3000,
    meta: {
      verifyToken: env.META_VERIFY_TOKEN || '',
      appSecret: env.META_APP_SECRET || '',
      pageAccessToken: env.META_PAGE_ACCESS_TOKEN || '',
      pageId: env.META_PAGE_ID || '1146970505169606',
      graphVersion: env.GRAPH_API_VERSION || 'v23.0',
    },
    businessName: env.BUSINESS_NAME || 'Becris Detailer',
    timezone: env.LEAD_TIMEZONE || 'America/New_York',
    sms: {
      accountSid: env.TWILIO_ACCOUNT_SID || '',
      authToken: env.TWILIO_AUTH_TOKEN || '',
      from: env.TWILIO_FROM_NUMBER || '',
      to: list(env.ALERT_SMS_TO),
    },
    email: {
      apiKey: env.RESEND_API_KEY || '',
      from: env.ALERT_EMAIL_FROM || 'Lead Alerts <onboarding@resend.dev>',
      to: list(env.ALERT_EMAIL_TO),
    },
    telegram: {
      botToken: env.TELEGRAM_BOT_TOKEN || '',
      chatIds: list(env.TELEGRAM_CHAT_ID),
    },
  };
}

export function enabledChannels(config) {
  const channels = [];
  if (config.sms.accountSid && config.sms.authToken && config.sms.from && config.sms.to.length) channels.push('sms');
  if (config.email.apiKey && config.email.to.length) channels.push('email');
  if (config.telegram.botToken && config.telegram.chatIds.length) channels.push('telegram');
  return channels;
}
