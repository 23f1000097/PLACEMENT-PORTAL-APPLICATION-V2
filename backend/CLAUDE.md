# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Flask backend for a role-based campus placement portal (Admin / Company / Student). Part of a larger repo
(`MAD-2-PROJECT/`) with a separate Vue 3 frontend in `../frontend`. This CLAUDE.md covers the `backend/` directory,
which is the primary working directory.

Stack: Flask + SQLAlchemy (SQLite) + Flask-JWT-Extended + Flask-Migrate + Flask-Caching (Redis) + Celery + Redis.

There is a root `../README.md` that was written as a gap-analysis / TODO list against an earlier state of the code.
**Treat it as historical, not authoritative** — many of the "critical gaps" it lists (Redis caching with targeted
invalidation, async CSV export, reminder emails actually sending, monthly reports emailed to admin, per-company
reports) have since been implemented. Verify current behavior by reading the code, not by trusting that document.

## Commands

Run all commands from `backend/` with the venv active (`venv\Scripts\activate` on Windows).

```bash
python run.py                    # dev server on http://127.0.0.1:5000
python seed_admin.py              # standalone admin seeder (admin is also auto-created on app start)

# Celery (separate terminals; Redis must be running)
celery -A celery_app.celery worker --loglevel=info -P solo   # -P solo required on Windows
celery -A celery_app.celery beat  --loglevel=info

# DB migrations (Flask-Migrate/Alembic)
flask db migrate -m "message"
flask db upgrade
```

There is no test suite in this repo (`migrations/` is currently empty and no `test_*.py` files exist) — don't assume
pytest/CI conventions are in place.

Default admin login: `admin@placement.com` / `admin123` (override via `ADMIN_EMAIL`/`ADMIN_PASSWORD` env vars).

## Architecture

- **`app.py`** — `create_app()` factory: initializes extensions, registers blueprints under `/api/*`, creates upload
  dirs, calls `db.create_all()` + `ensure_admin_user()` at startup (no migration-only workflow — tables are created
  directly). Module-level `app = create_app()` is what `run.py` and Celery's `tasks.py` import.
- **`extensions.py`** — shared singletons (`db`, `jwt`, `migrate`, `cors`, `cache`) initialized here, bound to the app
  in `create_app()`. Import these, not new instances.
- **`config.py`** — single `Config` class. Cache is Redis DB `/1`; Celery broker/result backend is Redis DB `/0`
  (kept separate deliberately). `JWT_ACCESS_TOKEN_EXPIRES` is configurable via env, default 3600s.
- **`celery_app.py`** — Celery app + beat schedule (daily reminders at 09:00, monthly report on the 1st at 08:00,
  `Asia/Kolkata` timezone). `tasks.py` does `from app import app` and wraps each task body in `with app.app_context()`.

### Models (`models/`)
`User` → 1:1 → `Student` or `Company` (role-specific profile, `cascade="all, delete"` from `User`).
`Company` → 1:N → `JobPosition` → 1:N → `Application` (unique constraint on `(student_id, job_id)` prevents duplicate
applications — `models/application.py`). `Placement` is a denormalized record (stores `company_name`/`job_title` as
plain strings, not just FKs) created when an `Application.status` transitions to `"Placed"` — see
`routes/company_routes.py` (`update_status`) and `routes/placement_routes.py`. Every model has a `to_dict()` used
directly as the JSON response shape — no separate serializer layer.

### Routes (`routes/`)
Blueprints registered under `/api/auth`, `/api/admin`, `/api/student`, `/api/company`, `/api/application`,
`/api/placement`. Auth: JWT with a `role` claim; `utils/decorators.py:role_required(role)` verifies the JWT, loads the
`User`, checks `is_active`, and checks role membership, stashing the user on `g.current_user`. `current_user()` is a
lighter helper for routes that just need the caller's identity. Companies must be admin-approved before their drives
are visible to students; drives (`JobPosition`) must be admin-approved before students can see/apply to them.

`routes/services/`:
- **`cache_service.py`** — `cached(timeout)` wraps `cache.cached()` with a key function that includes user id + query
  string (`make_cache_key`), so per-user/per-filter responses don't collide. `clear_cache(*prefixes)` does **targeted**
  Redis key deletion by prefix (falls back to `cache.clear()` only if no prefix given or the backend isn't Redis) —
  when adding/editing a cached listing route, always invalidate via the matching `*_PREFIX` constant instead of
  reaching for `cache.clear()` directly. Cached routes: `GET /api/student/drives`, `/api/admin/companies`,
  `/api/admin/students`, `/api/admin/jobs`.
- **`eligibility_service.py`** — `student_matches_job(student, job)` checks CGPA, branch, passing year, required
  skills, deadline, and approval status before allowing an apply; returns `(is_eligible, reasons[])`.
- **`report_service.py`** / **`pdf_service.py`** — admin/company stats and CSV/PDF generation, used both by
  synchronous routes and by Celery tasks in `tasks.py`.

### Async work (`tasks.py`)
All Celery tasks re-enter `app.app_context()` themselves. Email sending goes through `safe_send_email` (wraps
`utils/email.py:send_email`), which swallows `RuntimeError` when SMTP env vars aren't configured so tasks don't fail
in dev — check logs, not exceptions, if email "silently" doesn't go out locally. Tasks cover: deadline + interview
reminders (daily beat job), monthly admin report + per-company monthly report (emailed with PDF/HTML), status-change
and new-application notifications, and async CSV export for students/companies (route dispatches `.delay(...)`,
result is emailed when ready — see `export_student_applications`/`export_company_applications`).

### File uploads
`static/uploads/{resumes,company_logos,offer_letters}` — created at app startup. `utils/helper.py:save_file()` saves
with a UUID-based filename via `secure_filename` + `uuid4().hex`, avoiding collisions/traversal.
