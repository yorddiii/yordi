import { fetchLead } from './meta.js';
import { summarizeLead } from './format.js';
import { notifyAll } from './notify.js';

// Meta can deliver the same leadgen event more than once; remember recent IDs
// so the owner isn't texted twice for one lead.
const SEEN_TTL_MS = 24 * 60 * 60 * 1000;
const seen = new Map();

export function alreadySeen(leadgenId, now = Date.now()) {
  for (const [id, at] of seen) if (now - at > SEEN_TTL_MS) seen.delete(id);
  if (seen.has(leadgenId)) return true;
  seen.set(leadgenId, now);
  return false;
}

export async function handleLeadEvent(event, config, { fetchImpl = fetch, log = console } = {}) {
  if (alreadySeen(event.leadgenId)) {
    log.info(`[lead ${event.leadgenId}] duplicate delivery, skipped`);
    return null;
  }

  let lead = null;
  try {
    lead = await fetchLead(event.leadgenId, config.meta, fetchImpl);
  } catch (err) {
    // Still alert – a heads-up with a Leads Center link beats a silent miss.
    log.error(`[lead ${event.leadgenId}] could not fetch details: ${err.message}`);
  }

  const summary = summarizeLead(lead, { pageId: event.pageId || config.meta.pageId, timezone: config.timezone });
  const results = await notifyAll(summary, config, fetchImpl);
  for (const r of results) {
    if (r.ok) log.info(`[lead ${event.leadgenId}] ${r.channel} alert sent`);
    else log.error(`[lead ${event.leadgenId}] ${r.channel} alert FAILED: ${r.error}`);
  }
  return results;
}
