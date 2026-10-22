# Becris Detailer – Instant Meta Lead Alerts

The moment someone submits a **Facebook / Instagram Lead Ads form** for
**Becris Detailer LLC** (Page ID `1146970505169606`), the owner gets an alert
with the lead's name, phone, email, form answers and which ad they came from,
so they can call back within minutes instead of finding the lead hours later.

```
Lead submits form ─▶ Meta webhook ─▶ this service ─▶ fetch lead details (Graph API)
                                                  └▶ 📱 SMS  ✉️ Email  💬 Telegram  (any/all)
```

Example text message:

```
🚨 NEW LEAD – Becris Detailer

👤 Jane Doe
📞 +15715550199
✉️ jane@example.com

• What type of vehicle do you have? suv
• Which service do you need? full interior + exterior

Source: Facebook · form "Free Detailing Quote"
Ad: Fall Special – Interior Detail
Received: Thu, Oct 22, 2:05 PM

⏱ Call or text them now – speed wins the job!
```

The email version has **Call now**, **Text now** and **Open Leads Center** buttons.

### Built so leads don't slip through

- Verifies every webhook with the app secret (`X-Hub-Signature-256`), so nobody can fake leads.
- If the lead details can't be loaded (e.g. an expired token), it **still alerts** with a link to Leads Center.
- Sends on every configured channel in parallel; one channel failing doesn't block the others.
- Ignores Meta's duplicate deliveries, so one lead = one alert.
- No dependencies – plain Node.js 18+.

---

## Setup (≈30 minutes, one time)

### 1. Pick how the owner gets notified

Fill in at least one channel (see `.env.example`):

| Channel | Best for | What you need |
| --- | --- | --- |
| **SMS (Twilio)** – recommended | Loudest; can't miss it | Twilio account + phone number. US numbers must be registered for A2P 10DLC (or use a verified toll-free number) or texts may be blocked. |
| **Email (Resend)** | A record of every lead | Resend API key; verify a sending domain (or use `onboarding@resend.dev` while testing). |
| **Telegram** | Free, instant push | Create a bot with [@BotFather](https://t.me/BotFather), message it once from the owner's phone, then get the chat ID from `https://api.telegram.org/bot<TOKEN>/getUpdates`. |

### 2. Deploy the service

Any Node host with a public HTTPS URL works. With **Render**: push this repo,
choose *New → Blueprint*, select the repo, and fill in the secrets that
`render.yaml` asks for. You'll get a URL like `https://becris-lead-alerts.onrender.com`.

> Use an always-on plan. Free tiers that sleep add up to a minute of delay to the first alert after idle time.

Check it's alive: opening `https://<your-url>/` shows `{"ok":true,"channels":[...]}`.

### 3. Connect Meta

1. **Create an app** at [developers.facebook.com](https://developers.facebook.com/apps) (type *Business*), owned by the business that manages the Becris Detailer LLC page. Copy **App secret** (Settings → Basic) into `META_APP_SECRET`.
2. **Get a Page access token** that doesn't expire. Easiest: Business Settings → Users → **System users** → add one, give it the *Becris Detailer LLC* page asset, then *Generate token* for your app with these permissions:
   `leads_retrieval`, `pages_show_list`, `pages_read_engagement`, `pages_manage_metadata`, `pages_manage_ads`.
   Use that token to get the page token:
   ```
   curl "https://graph.facebook.com/v23.0/1146970505169606?fields=access_token&access_token=<SYSTEM_USER_TOKEN>"
   ```
   Put the returned `access_token` in `META_PAGE_ACCESS_TOKEN`.
3. **Add the webhook**: in the app, add the *Webhooks* product → choose **Page** → *Subscribe to this object*:
   - Callback URL: `https://<your-url>/webhook`
   - Verify token: the value of `META_VERIFY_TOKEN`

   Then subscribe to the **`leadgen`** field.
4. **Subscribe the page to the app**:
   ```
   curl -X POST "https://graph.facebook.com/v23.0/1146970505169606/subscribed_apps?subscribed_fields=leadgen&access_token=<PAGE_ACCESS_TOKEN>"
   ```
   It should return `{"success":true}`.
5. **Switch the app to Live** mode (top of the app dashboard).
6. If the page uses **Leads Access Manager** (Business Settings → Integrations → Leads Access), give your app access there, or Meta won't send it leads.

### 4. Test it

- `npm run test-alert` (locally with a filled-in `.env`) sends a fake lead through every channel, to confirm the owner's phone and inbox receive alerts.
- End to end: open Meta's [Lead Ads Testing Tool](https://developers.facebook.com/tools/lead-ads-testing), pick the page and form, and click **Create lead**. The alert should arrive within a few seconds. Check the service logs for `[lead …] sms alert sent`.

---

## Running locally

```bash
cp .env.example .env    # fill in values
npm start               # starts on PORT (default 3000)
npm test                # unit + webhook tests (no network needed)
```

To let Meta reach a local machine, expose it with a tunnel such as `ngrok http 3000` and use that HTTPS URL as the callback.

## Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| Meta says "callback URL couldn't be validated" | `META_VERIFY_TOKEN` doesn't match, or the service isn't reachable over HTTPS. |
| Logs show `Rejected webhook … invalid signature` | `META_APP_SECRET` is wrong. |
| Alert says "details could not be loaded" | Page token expired or lacks `leads_retrieval`; or the app has no access in Leads Access Manager. The log line shows Meta's exact error. |
| No logs at all when a test lead is created | Page not subscribed (step 3.4), `leadgen` field not subscribed, or app still in Development mode. |
| SMS log says sent but no text arrives | Twilio number not registered for A2P 10DLC / toll-free verification. |
