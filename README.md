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
2. Run `py app.py` (or `python3 app.py`). Register an account in the browser.
3. It prints two URLs, e.g. `Running on http://192.168.1.235:5000`. On your
   phone (same WiFi), open that second address in a browser.
4. Stop it any time with Ctrl+C. Your laptop must stay on and awake for your
   phone to reach it this way.

## Deploy for real (reachable from anywhere, phone data included)

Production data lives in [Supabase](https://supabase.com) Postgres (schema
`daily_goals`), so a Render redeploy cannot wipe accounts. Register/login
still happen in the Flask app; the database is used as storage only.

1. In the Supabase SQL editor, run `supabase/migrations/001_daily_goals.sql`
   (or let the app create the schema on first boot via `init_db()`).
2. Copy **Project Settings → Database → Connection string** (URI). Prefer the
   **pooler** URI (port `6543`) and add `?sslmode=require` if it is missing.
3. Put this folder in its own git repository and push it to GitHub.
4. On Render: **New +** → **Blueprint** → connect the repo → Render reads
   `render.yaml`. Set `DATABASE_URL` to that URI. (`SECRET_KEY` is generated
   for you.)
5. Deploy. Render gives you a URL like `https://daily-goals-xxxx.onrender.com`.

Locally, omit `DATABASE_URL` to keep using a SQLite file (`daily_goals.db`),
or point `DATABASE_URL` / `SUPABASE_DB_URL` at the same database. A `.env`
file in this folder is loaded automatically.

**Free-tier notes, honestly:**
- Render spins down after ~15 minutes of no traffic and takes a few seconds
  to wake back up on the next visit — normal for a free instance, not a bug.
- Existing Turso/SQLite data is not migrated automatically. If you still
  have accounts there, export them before switching over.

## Files

- `app.py` — the Flask app (routes, sessions, API)
- `db.py` — SQLite locally / Supabase Postgres in production
- `supabase/migrations/` — Postgres schema for the `daily_goals` schema
- `templates/` — mobile-first pages (login, dashboard)
- `render.yaml` — one-click Render deployment config
- `requirements.txt` — Flask + gunicorn + psycopg

<!-- persistence test marker: Fri Jul 31 01:27:11 QST 2026 -->
<!-- turso persistence re-test: verified 2026-08-08T01:34:32Z -->
