# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**EKSTM** is a Django-based Staff Transport Management System for Emirates (EK). It manages driver duty cards, daily head counts, bus odometer readings, delay/breakdown reporting, STM route timetables, and driver document profiles (stored on Google Drive).

## Development Commands

```bash
# Activate environment
source venv/bin/activate

# Run development server
python manage.py runserver

# Apply migrations
python manage.py migrate

# Create superuser (admin access)
python manage.py createsuperuser

# Import seed data from CSV files in Drivers_Master/
python manage.py import_drivers
python manage.py import_dutycard_trips
python manage.py import_bus_master
python manage.py remove_duplicates

# Upload GPS/Salik/Mileage data (done via UI at /upload_gpsreports/, /upload_salik/, /upload_mileage/)
```

### React frontend (static/myapp/)

```bash
cd static/myapp
npm install
npm start        # dev server on :3000 (proxies API calls to Django)
npm run build    # outputs to static/myapp/build/ — copy assets to static/static/
```

### Tailwind CSS (project root)

```bash
npm install                          # installs tailwindcss, postcss, autoprefixer
npx tailwindcss -i ./src/input.css -o ./static/static/css/output.css --watch
```

## Environment

Requires a `.env` file in the project root:

```
SECRET_KEY=...
DEBUG=True
DB_NAME=staff_transport_db_pro
DB_USER=root
DB_PASSWORD=...
DB_HOST=localhost
DB_PORT=3306
TIME_ZONE=Asia/Dubai
```

Database is **MySQL**. `staff_transport/__init__.py` pins PyMySQL as the MySQL adapter. Google Drive OAuth credentials go in `credentials.json` (gitignored); the token is stored in `token.json` (also gitignored).

## Architecture

Single Django app: **`duty/`** — all models, views, forms, URLs, and templates live here.

### Frontend stack

The project uses **three frontend layers** that coexist:

| Layer | Where | Used for |
|---|---|---|
| Django templates + Bootstrap 4/5 | `duty/templates/duty/` | All main pages |
| Tailwind CSS utility classes | `package.json` (root) | `ekstm_47seater_report_dashboard.html` card colours (`bg-yellow-200`, `bg-red-200`) |
| React 18 + axios | `static/myapp/` | Staff ID / driver name autocomplete form (`App.js`) — built output lives in `static/static/` |

Most templates are **standalone** (no `{% extends %}`). Only auth templates and `User_Interface_stmtimetable.html` extend `base_generic.html`. The admin dashboard and STM dashboard embed all CSS/JS inline.

### Template → API wiring

Key templates make `fetch()` calls directly to JSON endpoints — no separate API layer:

| Template | Calls |
|---|---|
| `admin_dashboard.html` | `GET /dashboard/data/`, `GET /dashboard/duty-card-submission-data/` |
| `STM_dashboard.html` | `GET /api/fleet-counts/`, `GET /get-most-delayed-trips-api/`, `GET /get-otp-chart-data/`, `GET /get-daily-delay-details/`, `GET /get-otp-details/`, `GET /filter-dashboard/`, `GET /get-top-delayed-load-trips-api/` |
| `enter_head_count.html` | `GET /get-duty-card-details/`, `GET /staff-id-autocomplete/`, `GET /get-driver-name/` |
| `submit_bus_km.html` | `GET /ajax/duty_card_suggestions/`, `GET /ajax/bus_no_suggestions/` |
| `ekstm_47seater_report_dashboard.html` | `GET /bus_trip_details/<bus_code>/` |

### Views package — `duty/views/`

The views are split by domain. Each module is self-contained with its own imports:

| Module | Responsibility |
|---|---|
| `auth.py` | signup, logout, password reset, login |
| `driver.py` | home, head count entry, submission history, duty card / driver autocompletes |
| `reports.py` | admin dashboard, DataTables report, Excel downloads, delay & breakdown form submissions |
| `stm.py` | STM route search, timetable detail, OTP chart API, delay detail APIs, fleet counts, public dashboards |
| `upload.py` | Cabin crew Excel processing, GPS/Salik/Mileage CSV uploads |
| `bus.py` | Bus KM submission, EKSTM 47-seater fleet dashboard, bus/duty card autocompletes |
| `profile.py` | Driver profile CRUD, Google Drive file upload, OAuth2 callback, Drive image proxy |
| `__init__.py` | Re-exports everything — `urls.py` imports from here without changes |

### Access control — `duty/decorators.py`

`admin_required` decorator: blocks regular drivers from admin-only views. Logic:
1. `is_staff` or `is_superuser` → always allowed through
2. Exists in `DriverImportLog` → blocked, renders `duty/access_denied.html`
3. Otherwise → allowed through

Alias `user_in_driverimportlog_required` exists for backward compatibility.

### Key models — `duty/models.py`

- **`DriverImportLog`** — driver master list (name + staff_id). Staff ID is used as the Django `User.username`.
- **`DutyCardTrip`** — scheduled trips per duty card (route, times, capacity). Seeded from CSV.
- **`DriverTrip`** — driver's daily head count submission (links driver + duty card).
- **`BusKmTracking`** — odometer readings submitted per trip.
- **`DelayData`** — delay reports with STD/ATD/STA/ATA times; delay is auto-calculated.
- **`BreakdownReport`** — vehicle incident reports.
- **`StmRoute / StmPickupPoint / StmShiftTime`** — STM timetable data (route → stops → shift times).
- **`Unit / EKSTMDailyTrips / EKSTMMileage / EKSTMSalik`** — EKSTM 47-seater fleet tracking (GPS trips, odometer totals, toll crossings).
- **`DriverProfile`** — extended driver document store; file IDs point to Google Drive (not local storage).

### URL structure — `duty/urls.py`

All URLs are rooted at `/` (included in `staff_transport/urls.py`). Django admin sits at `/admin/`. Notable groupings:

- `/` `/enter_head_count/` `/submit-bus-km/` `/submission-history/` — driver daily workflow
- `/dashboard/` `/report/` `/ekg-report/` `/add_delay_report/` `/ekg-breakdown/` — admin/supervisor views
- `/stm-dashboard/` `/search/` `/route-details/` `/stm_timetables/` `/public-stm-dashboard/` — STM route and OTP views
- `/ekstm_47seater_report_dashboard/` `/upload_gpsreports/` `/upload_salik/` `/upload_mileage/` — EKSTM fleet views
- `/profile/` `/oauth2callback/` `/profile/image/<file_id>/` — driver profile and Drive integration
- `/upload/` `/download/<filename>/` — cabin crew Excel processing
- All `/api/`, `/ajax/`, `/get-*`, `/filter-*` paths are JSON-only endpoints consumed by frontend JS

### Authentication flow

- Users sign up via `/signup/` — `CustomUserCreationForm` validates the `staff_id` exists in `DriverImportLog` before creating a `User`.
- Regular drivers (`DriverImportLog` members) access: home, head count entry, bus KM submission, submission history, profile.
- Admin users (`is_staff=True`, not in `DriverImportLog`) access: dashboard, reports, delay/breakdown entry, subcategory selection.
- Password reset is done without email — staff ID + email verification only, no token expiry.

### Forms — `duty/forms.py`

| Form | Used in |
|---|---|
| `DriverTripForm / DriverTripFormSet` | Head count submission — validates head count 0–47 |
| `CustomUserCreationForm` | Signup — validates staff_id exists in `DriverImportLog` before creating `User` |
| `PasswordResetRequestForm / SetNewPasswordForm` | Password reset flow |
| `DelayDataForm` | EKG delay report — auto-calculates `delay` from STA/ATA in `clean()` |
| `BreakdownReportForm` | EKG breakdown incident report |
| `BusKmTrackingForm` | Bus KM submission — `duty_card_no` field is readonly in widget |
| `DriverProfileForm` | Driver profile — includes 6 extra `FileField`s for Drive uploads (not model fields) |
| `UploadFileForm` | Cabin crew Excel upload |

### Google Drive integration — `duty/utils.py`

`upload_file_to_drive()` handles both in-memory and temp-file uploads. If no valid token exists, it returns an OAuth `auth_url`; the view redirects to Google and the callback lands at `/oauth2callback/`, which passes the code back to `/profile/`. The `drive_image_proxy` view proxies Drive images through the app's own domain to avoid browser blocking.

### Data upload flows

- **Cabin crew** — inbound/outbound Excel files uploaded via `/upload/`, processed by `_process_files()` in `upload.py` which groups by building clusters and calculates unit counts.
- **GPS reports / Salik / Mileage** — CSV files uploaded via `/upload_gpsreports/`, `/upload_salik/`, `/upload_mileage/` using `update_or_create` to avoid duplicates.

## Known Issues to Be Aware Of

- `EKSTMSalik.salik_satrt_time` has a typo baked into the DB column name — do not rename without a migration.
- `set_new_password` is now gated by a `password_reset_user_id` session flag set only after the staff_id + email check in `password_reset_request` (closes the prior IDOR where any account could be reset by guessing the URL id). Note: still no time-based expiry on the verification — it lives for the session.
- `DriverImportLog.staff_id` has `unique=False` but duplicates cause problems; `remove_duplicates` management command exists for cleanup.
- `AutoLogoutMiddleware` in `duty/middleware.py` is defined but **not registered** in `MIDDLEWARE` and is effectively dead code.
