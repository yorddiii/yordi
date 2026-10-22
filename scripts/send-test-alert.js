// Sends a fake lead through every configured channel so you can confirm the
// owner's phone/inbox actually receives alerts. Usage: npm run test-alert
import { loadDotEnv, getConfig, enabledChannels } from '../src/config.js';
import { summarizeLead } from '../src/format.js';
import { notifyAll } from '../src/notify.js';

loadDotEnv();
const config = getConfig();

if (!enabledChannels(config).length) {
  console.error('No notification channel configured. Fill in Twilio, Resend, or Telegram settings in .env first.');
  process.exit(1);
}

const sampleLead = {
  id: 'TEST-LEAD',
  created_time: new Date().toISOString(),
  platform: 'fb',
  form_name: 'TEST – Detailing quote',
  ad_name: 'TEST ad',
  campaign_name: 'TEST campaign',
  field_data: [
    { name: 'full_name', values: ['Test Customer'] },
    { name: 'phone_number', values: ['+15555550123'] },
    { name: 'email', values: ['test.customer@example.com'] },
    { name: 'what_type_of_vehicle_do_you_have?', values: ['SUV'] },
    { name: 'which_service_are_you_interested_in?', values: ['full_interior_+_exterior_detail'] },
  ],
};

const summary = summarizeLead(sampleLead, { pageId: config.meta.pageId, timezone: config.timezone });
const results = await notifyAll(summary, config);
for (const r of results) console.log(`${r.ok ? '✅' : '❌'} ${r.channel}${r.error ? ` – ${r.error}` : ''}`);
process.exit(results.every((r) => r.ok) ? 0 : 1);
