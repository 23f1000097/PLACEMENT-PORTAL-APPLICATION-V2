# Placement Portal Application – V2 (MAD-II)

A role-based campus recruitment portal for **Admin (Institute)**, **Companies**, and **Students**.
Backend: **Flask + SQLAlchemy + SQLite + JWT + Celery + Redis**. Frontend: **Vue 3 + Pinia + Vue Router + Bootstrap 5**.

---

## 1. Current Architecture (as-built)

```
MAD-2-PROJECT/
├── backend/
│   ├── app.py                 # create_app(), blueprint registration, ensure_admin_user()
│   ├── run.py                 # dev entry point
│   ├── config.py              # Config (DB, JWT, cache, Celery/Redis, uploads)
│   ├── extensions.py          # db, jwt, migrate, cors, cache singletons
│   ├── celery_app.py          # Celery instance + beat schedule
│   ├── tasks.py               # Celery tasks (reminders, reports, notifications, CSV)
│   ├── seed_admin.py          # standalone admin seeder
│   ├── models/                # User, Student, Company, JobPosition, Application, Placement
│   ├── routes/                # auth, admin, company, student, application, placement
│   │   └── services/          # cache, eligibility, report, pdf
│   └── utils/                 # decorators, email, validators, helper
└── frontend/
    └── src/
        ├── views/             # AuthPage, Admin/Company/Student dashboards
        ├── components/        # Panel, ApplicationTable
        ├── stores/ppa.js      # single Pinia store (all state + API calls)
        ├── services/api.js    # axios client w/ JWT interceptor
        └── router/index.js    # 4 routes
```

**What already works well (do not rebuild):**

- ✅ All 6 models with relationships, cascade deletes, and a **unique constraint on `(student_id, job_id)`** preventing duplicate applications (`models/application.py`).
- ✅ Admin is **pre-created programmatically** (`app.py:ensure_admin_user` + `seed_admin.py`).
- ✅ JWT auth with `role` claim + `role_required` decorator (`utils/decorators.py`); students self-register, companies register (approval-gated), admin login-only.
- ✅ Approval gates: companies need admin approval before dashboard/drives; drives need admin approval before students see them.
- ✅ Eligibility validation (CGPA, branch, year, skills, deadline) before apply (`services/eligibility_service.py`).
- ✅ Placement auto-created when an application is marked `Placed`.
- ✅ Celery tasks + beat schedule exist; email notifications on apply / status change.
- ✅ Functional Vue dashboards for all three roles.

The sections below are the **changes still required** to satisfy every core milestone. They are ordered by priority.

---

## 2. Critical Gaps (must fix for core milestones)

### 2.1 Caching is NOT using Redis and is NOT applied anywhere — *Milestone: Redis Caching*
This milestone is effectively unimplemented.

- **`config.py`** uses `CACHE_TYPE = "SimpleCache"`. The spec mandates **Redis**. Change to:
  ```python
  CACHE_TYPE = "RedisCache"
  CACHE_REDIS_URL = os.getenv("CACHE_REDIS_URL", "redis://localhost:6379/1")
  CACHE_DEFAULT_TIMEOUT = 300
  ```
  (Use DB `/1` so cache is separate from the Celery broker on `/0`.)
- **`services/cache_service.py`** defines a `cached()` decorator that is **never used**. Apply caching to the read-heavy endpoints named in the milestone:
  - `GET /api/student/drives` and student dashboard drive list (job listings)
  - `GET /api/admin/companies` (company search)
  - `GET /api/admin/students` (student search)
  - `GET /api/admin/jobs`
- **Cache invalidation:** `clear_cache()` calls `cache.clear()`, which wipes *everything*. Replace with **targeted key deletion** (e.g. delete the job-list keys when a job is created/approved/updated/deleted, in `company_routes.py` and `admin_routes.py`). Because query strings vary (search/filter), use `key_prefix` or a `make_cache_key` that folds in `request.args`.
- Add **cache-expiry** proof (timeout values) and document the refresh policy in the report.

### 2.2 CSV Export runs synchronously — *Milestone: Celery Jobs (User-triggered CSV)*
The requirement is an **async batch job that alerts when done**. Currently `student_routes.py:export_applications` calls `export_student_applications_csv(...)` **directly** (blocking), even though the Celery task `tasks.export_student_applications` already exists and is unused.

Changes:
- Rewire the route to dispatch the task: `task = export_student_applications.delay(student.id)` and return `202 Accepted` with `task_id`.
- Add a **status/download endpoint**, e.g. `GET /api/student/applications/export/<task_id>` that reports Celery task state and, when ready, returns the file (or a download URL). Use `send_file`.
- Send the **"export ready" alert** (email or in-app message) from inside the task once the CSV is written.
- **Company CSV export is missing entirely.** The milestone says "students **and companies** can export application and placement history." Add a company export route + task (reuse the pattern).

### 2.3 Daily reminder task builds a list but never sends anything — *Milestone: Celery Jobs (Reminders)*
`tasks.send_daily_deadline_reminders` computes `reminders` and **returns them without calling `send_email`**. It does nothing user-visible.

Changes:
- Actually **dispatch** each reminder (loop → `send_email(...)`, or fan out to a per-student subtask).
- The milestone reframes this as an **Interview Reminder Job**: "send reminders to students **with scheduled interviews**." Add logic that also finds `Application.interview_at` within the next 24h and reminds those students. Keep the deadline reminder too (both are in scope).
- (Optional per spec) add a **Google Chat webhook** or **SMS** channel alongside email in `utils/email.py` / a new `utils/notify.py`.

### 2.4 Monthly report is never emailed and counts are all-time — *Milestone: Celery Jobs (Reports)*
`tasks.generate_monthly_activity_report` returns HTML but **never emails the admin**, and `services/report_service.py:admin_stats()` / `monthly_activity_report()` count **all-time** totals, not the current month.

Changes:
- In the task, render the report and **`send_email(...)` to the admin address** (the spec: "Sent to admin via email"). Attach the PDF (via `pdf_service`) or send HTML inline — offer both, since HTML/PDF choice is allowed.
- Add **month-scoped** stats: number of drives conducted, applications, and selections **for the reporting month** (filter by `created_at` / `applied_at` / `placed_at` between month start and end). The current all-time numbers are misleading in a "monthly" report.
- Milestone also asks for **per-company** monthly reports — add a company variant.

### 2.5 Admin cannot *remove* companies or drives — *Milestone: Admin Dashboard*
The milestone says "**Approve and Remove** Company profiles" and "**Approve and Remove** job posting/placement drives." Only approve/reject toggles exist.

Changes:
- Add `DELETE /api/admin/companies/<id>` and `DELETE /api/admin/jobs/<id>` (cascade already handles children).
- Optionally distinguish **blacklist** from **deactivate**: today only `User.is_active` exists. If you want a true blacklist per the spec, add a `blacklisted` boolean (or reuse `is_active` and label it clearly in the UI).

---

## 3. Frontend Changes (Vue milestones)

### 3.1 Add route guards
`router/index.js` has **no navigation guards** — typing `/admin` in the URL loads the admin view shell regardless of role (the API still blocks data, but the UX is wrong). Add a `beforeEach` guard that checks the Pinia store's `isLoggedIn` + `user.role` and redirects unauthorized users to `/`.

### 3.2 Interview scheduling & offer-letter download (Student/Company milestones)
- Company: expose **interview scheduling** clearly. `interview_at` is currently buried in the status draft; add a dedicated date-time control when moving a candidate to `Interview`.
- Student milestone requires **"Download offer letters or placement confirmations."** The `Application.offer_letter` field exists but there is **no upload (company) → download (student)** flow. Add:
  - Company upload endpoint for an offer letter (or a **dummy offer-letter generator** — an allowed optional feature; reuse `pdf_service`).
  - Student download button wired to it.

### 3.3 Validation
- Backend validation is thin: numeric fields (`cgpa`, `salary`, `vacancies`, `passing_year`) are accepted as raw strings from the client and stored unchecked; email validation is naive (`"@" in email`). Add server-side coercion + range checks in `utils/validators.py` and the create/update routes.
- Frontend already uses some HTML5 validation; extend `required`/`min`/`max`/`type` on the job and profile forms.

### 3.4 Optional milestones (only after core is done)
- **Chart.js analytics** — `chart.js` is already a dependency but unused. Add placement-trend / applications-funnel charts to the Admin dashboard.
- **Public landing dashboard** (pre-login, read-only aggregate stats).
- **PWA** — add `manifest.json` + service worker for "Add to Home Screen."
- **ATS resume screener** — `scikit-learn` + `pandas` are installed; build a keyword/skill-match scorer.

---

## 4. Housekeeping / Correctness

- **Trim `requirements.txt`.** It currently pulls in the entire **TensorFlow/TensorBoard** stack (`tensorboard`, `absl-py`, `h5py`, `ml_dtypes`, `grpcio`, `flatbuffers`, `libclang`, `astunparse`, `gast`, `google-pasta`, `keras`-adjacent `namex`, `opt_einsum`, `optree`, `termcolor`, `wrapt`). **None are used.** The rubric disallows frameworks outside the approved list — remove them to avoid confusion. Keep only: Flask, Flask-SQLAlchemy, Flask-JWT-Extended, Flask-Migrate, Flask-Caching, flask-cors, celery, redis, reportlab, python-dotenv, (and pandas/scikit-learn only if you build the ATS/CSV-with-pandas features).
- **Two SQLite DB files exist** (`backend/database/placement.db` and `placement_portal.db`); config only uses `placement_portal.db`. Delete the stray `placement.db`. (`.gitignore` already excludes `*.db` and `backend/database/` — good, they should not be committed.)
- **Celery app context:** `tasks.py` does `from app import app` and wraps each task in `with app.app_context()`. This works, but consider a `ContextTask` base so context is automatic and the app isn't re-created oddly. Low priority.
- **SMTP config:** email requires `SMTP_USERNAME`/`SMTP_PASSWORD` env vars or `send_email` raises. Add a **`.env.example`** documenting `SMTP_*`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `CELERY_BROKER_URL`, `CACHE_REDIS_URL`.
- **JWT expiry** is default (15 min). Set `JWT_ACCESS_TOKEN_EXPIRES` explicitly in `config.py`.
- **Milestone 0:** this root `README.md` now satisfies the "add README.md with project description" requirement. Also confirm collaborator `MADII-cs2006` is added and each milestone is committed with its **unique commit message**.

---

## 5. Prioritized Action List

| # | Change | Milestone | Files |
|---|--------|-----------|-------|
| 1 | Switch cache to Redis + apply `@cached` to job/company/student listings + targeted invalidation | Redis Caching | `config.py`, `cache_service.py`, `admin_routes.py`, `student_routes.py`, `company_routes.py` |
| 2 | Make CSV export async (dispatch task, add status/download endpoint, alert on done) + add company export | Celery Jobs | `student_routes.py`, `company_routes.py`, `tasks.py` |
| 3 | Actually send daily reminders + add interview reminders | Celery Jobs | `tasks.py`, `utils/email.py` |
| 4 | Email monthly report to admin + month-scoped stats + company reports | Celery Jobs | `tasks.py`, `report_service.py` |
| 5 | Admin delete company/drive endpoints (+ optional blacklist flag) | Admin Dashboard | `admin_routes.py`, `models/user.py` |
| 6 | Vue route guards | Auth/RBAC | `router/index.js`, `stores/ppa.js` |
| 7 | Offer-letter upload/download (or dummy generator) + explicit interview scheduling UI | Student/Company | `company_routes.py`, `student_routes.py`, `pdf_service.py`, dashboards |
| 8 | Stronger backend + frontend validation | UI/UX | `validators.py`, routes, Vue forms |
| 9 | Clean `requirements.txt`, remove stray DB, add `.env.example` | Housekeeping | `requirements.txt`, `database/`, new `.env.example` |
| 10 | (Optional) Chart.js, public landing page, PWA, ATS screener | Enhancements | frontend |

---

## 6. Setup & Run

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate            # Windows
pip install -r requirements.txt
python seed_admin.py             # creates admin (also auto-created on app start)
python run.py                    # http://127.0.0.1:5000
```

### Redis + Celery (separate terminals, Redis must be running)
```bash
celery -A celery_app.celery worker --loglevel=info -P solo   # -P solo on Windows
celery -A celery_app.celery beat  --loglevel=info
```

### Frontend
```bash
cd frontend
npm install
npm run dev                      # http://127.0.0.1:5173
```

**Default admin:** `admin@placement.com` / `admin123` (override via `ADMIN_EMAIL` / `ADMIN_PASSWORD`).

---

## 7. Issue / Progress Log
_(Track milestone completion and blockers here, per the tracking guidance.)_

- [ ] Redis caching wired and invalidated
- [ ] CSV export async + alert
- [ ] Reminder emails actually send
- [ ] Monthly report emailed to admin (month-scoped)
- [ ] Admin remove company/drive
- [ ] Route guards
- [ ] Offer letter flow
- [ ] requirements.txt cleaned
```
