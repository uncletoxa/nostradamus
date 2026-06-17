# PWA + Web Push Notifications — work in progress

Branch: `pwa-push-notifications`

Adds PWA installability ("Add to Home Screen") and Web Push notifications.
Two notification types:
1. **Chat** — push to all other subscribers when someone posts a chat message.
2. **Prediction reminders** — push to subscribed users who have not predicted
   for matches starting within N hours (cron-driven management command).

No iOS / no app store / no APK — Android Chrome installs straight from the URL.

---

## What's done (code complete)

### New `notifications/` app
- `models.py`
  - `PushSubscription` — per-device endpoint + p256dh/auth keys, FK to User.
  - `PredictionReminderSent` — dedupe table (unique user+match) so reminders
    are sent at most once per match.
- `utils.py` — `send_push()` / `send_push_to_users()` using `pywebpush` + VAPID.
  Auto-deletes dead subscriptions on HTTP 404/410.
- `views.py` — `subscribe`, `unsubscribe`, `vapid_public_key`, and `service_worker`
  (serves `/sw.js` from site root so its scope covers the whole app).
- `urls.py` — mounted at `/push/`.
- `management/commands/generate_vapid_keys.py` — one-time VAPID keypair generator.
- `management/commands/send_prediction_reminders.py` — `--hours N` (default 3).

### Static / frontend
- `static/manifest.json` — installable PWA manifest.
- `static/js/sw.js` — service worker: `push` + `notificationclick` handlers.
- `static/img/icon-192.png`, `icon-512.png` — generated from `logo.png`.
- `templates/base.html`
  - manifest link + `theme-color` meta in `<head>`.
  - 🔔 navbar toggle button (authenticated users only).
  - SW registration + push subscribe/unsubscribe JS before `</body>`.

### Modified
- `requirements.txt` — added `pywebpush==2.0.0`.
- `nostradamus/settings.py`
  - registered `notifications` app.
  - added `VAPID_PRIVATE_KEY` / `VAPID_PUBLIC_KEY` / `VAPID_CONTACT_EMAIL` config.
  - added `basic.context_processors.vapid_public_key` context processor.
- `nostradamus/urls.py` — `/push/` include + `/sw.js` route.
- `basic/context_processors.py` — `vapid_public_key` (exposes key to templates).
- `chat/views.py` — `_notify_chat()` fires push to other subscribers on new message.
- `.gitignore` — ignores `vapid_private.pem`.

---

## Completed TODO items

1. **DB migration** — `0001_initial.py` generated and applied (PushSubscription + PredictionReminderSent).
2. **VAPID keys** — generated for local dev, added to `.env.local`.
   NOTE: prod needs its OWN keypair (`python manage.py generate_vapid_keys` on the server).
3. **Verified locally**:
   - Bell button renders in navbar for authenticated users.
   - `/sw.js` serves correctly with `Service-Worker-Allowed: /`.
   - `send_prediction_reminders --hours 24` found upcoming matches, attempted pushes,
     and created dedupe records in `PredictionReminderSent`.
   - Chat notification hook (`_notify_chat`) is wired in `chat/views.py`.

## TODO — remaining

1. **Wire the reminder cron** on prod alongside the existing score updater:
   ```
   python manage.py send_prediction_reminders --hours 3
   ```
   Run every 30–60 min.

2. **Deploy to prod** — rebuild image, generate prod VAPID keys, add to `.env`, run migrate.

3. **End-to-end test on prod** (Web Push requires HTTPS):
   - Install prompt + bell toggle subscribes/unsubscribes.
   - Post a chat message from another user → push arrives.
   - `send_prediction_reminders` with an upcoming SCHEDULED match → push arrives.

---

## Notes / decisions
- `pywebpush==2.0.0` pulls `py-vapid` (used by `generate_vapid_keys`).
- Dead-subscription cleanup is handled in `utils.send_push` on 404/410.
- The 🔔 button only shows for authenticated users and only after the service
  worker registers successfully.
- `sw.js` is served from root (`/sw.js`) via a Django view with
  `Service-Worker-Allowed: /` so its scope is the whole site, not `/static/`.
