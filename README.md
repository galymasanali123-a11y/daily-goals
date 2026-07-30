# Daily Goals

A small, mobile-friendly daily routine tracker, installable as a real app icon
on your phone (PWA — no App Store needed). Standalone from the desktop
MedStudy Assistant — separate login, separate data. Starts blank; add your
own routine (make the bed, drink water, whatever) right in the app.

**Features:** add/edit/delete/reorder goals, daily checklist with a
completion count, a day-streak counter, and a 7-day history strip. All
interactions are instant (no page reloads) and work offline once loaded.

## Install it as a real app (not "from Chrome")

Once it's running (see below) and you've opened the URL on your phone:

- **iPhone (Safari)**: tap the Share icon → **Add to Home Screen**.
- **Android/Xiaomi (Chrome)**: tap **⋮** → **Add to Home screen** (or Chrome
  may prompt "Install app" automatically).

It then opens full-screen with its own icon — no address bar, no browser UI.

## Try it tonight, free, no hosting account (same WiFi only)

1. Install dependencies: `pip install -r requirements.txt`
2. Set a password and run:
   - Windows PowerShell: `$env:APP_PASSWORD="yourpassword"; py app.py`
3. It prints two URLs, e.g. `Running on http://192.168.1.235:5000`. On your
   phone (same WiFi), open that second address in a browser.
4. Stop it any time with Ctrl+C. Your laptop must stay on and awake for your
   phone to reach it this way.

## Deploy for real (reachable from anywhere, phone data included)

Using [Render.com](https://render.com)'s free tier — no credit card needed.

1. Put this `daily_goals_app` folder in its own git repository (or a
   subfolder of one) and push it to GitHub.
2. On Render: **New +** → **Blueprint** → connect the repo → Render reads
   `render.yaml` and sets everything up automatically.
3. When prompted, set the `APP_PASSWORD` environment variable to whatever
   password you want to log in with. (`SECRET_KEY` is generated for you.)
4. Deploy. Render gives you a URL like `https://daily-goals-xxxx.onrender.com`
   — open that on your phone or laptop, anywhere, anytime.

**Free-tier notes, honestly:**
- The service spins down after ~15 minutes of no traffic and takes a few
  seconds to wake back up on the next visit — normal for a free instance,
  not a bug.
- The SQLite database lives on the service's local disk. It survives
  restarts, but a fresh **deploy** (e.g. pushing new code) can reset it on
  Render's free plan. If your goal history starts to matter long-term, add a
  Render persistent Disk (small paid add-on) and point `DB_PATH` at it.

## Files

- `app.py` — the whole backend (Flask, single file, SQLite storage)
- `templates/` — mobile-first pages (login, dashboard)
- `render.yaml` — one-click Render deployment config
- `requirements.txt` — Flask + gunicorn (the production server Render runs)
