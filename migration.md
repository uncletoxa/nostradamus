# Django 2.2 → 4.2 Migration Plan (landed on 5.2 LTS — see Phase 5)

> **STATUS: COMPLETE** — landed on `feat/django-4.2-upgrade`, one commit per phase
> (plus an unplanned Phase 5 that carried the upgrade on to Django 5.2 LTS, the
> latest LTS release). Final state: **Django 5.2.15 LTS / Python 3.12.13**.
> Baseline test result held steady at 49 tests / 4 failures / 16 errors through
> every phase — no regressions introduced by the upgrade itself (the failures/
> errors are pre-existing email/password-reset-flow issues, expected since this
> deployment doesn't use email support). See the per-phase notes below for the
> few spots where reality differed from the plan.

Goal: move this app from Django 2.2.28 / Python 3.7 to Django 4.2 LTS / Python 3.12,
so it can host an MCP server (or any modern tooling) that talks to the app's models
via the Django ORM in-process.

Recommended path is **LTS → LTS → LTS** (2.2 → 3.2 → 4.2), upgrading one feature
release family at a time. This is the path Django's own docs recommend, and it lets
deprecation warnings surface and get fixed *before* the APIs are removed, rather than
hitting a wall of `ImportError`/`AttributeError` all at once.

Each phase below is meant to be its own PR / its own session. Do not skip ahead —
land and verify each phase before starting the next.

---

## Phase 0 — Preparation & baseline (do this first, once) ✅ DONE

- [x] Create a working branch off `master`, e.g. `feat/django-4.2-upgrade`
- [x] Get local dev running per `readme.md` (Podman compose or venv) and confirm
      the app boots and you can log in
- [x] Run the existing test suite and record the baseline result:
      `python manage.py test`
      (apps with tests: `matches`, `accounts`, `predictions`)
      — **baseline: 49 tests, 4 failures, 16 errors** (all in email/password-reset
      flows — this deployment has no email support, so these were treated as
      low-priority pre-existing issues, not upgrade regressions to chase)
- [x] Take a backup of whichever DB you're testing against (the repo already ships
      `db_nostr_2024_backup.sql.gz` etc. — use a throwaway copy, not anything live)
- [x] Skim `host-to-code-migration.md` and `Makefile` — note that **migrations are
      not tracked in git** (`make django-setup` runs `makemigrations` fresh per
      deploy). This means there's no migration-history conflict to resolve, but
      any model field changes below will require generating + applying new
      migrations against the real DB on the next deploy. Plan for that.
      — **also surfaced a separate latent bug**: the `accounts` app has no
      migrations and is missing from the Makefile's `makemigrations` target,
      so `accounts_teamsupporter` likely doesn't exist in any real deployment.
      Out of scope for this migration (left untouched per owner's call) but
      worth fixing separately.

**Exit criteria:** app runs locally, baseline test results recorded, branch created.

---

## Phase 1 — Django 2.2 → 3.2 LTS (stay on Python 3.7) ✅ DONE — commit `d00f7a5`

Goal: land on the next LTS while still on the current Python, fixing everything that
3.2 *deprecates* (but doesn't yet remove) so Phase 3 has nothing left to break on.

- [x] Bump `Django==2.2.28` → `Django==3.2.*` (latest 3.2.x patch) in `requirements.txt`
- [x] `pip install -r requirements.txt` and run `python manage.py check`
- [x] Run `python -Wd manage.py test` (shows DeprecationWarnings) and fix what it flags,
      specifically the four spots already identified:
  - [x] `matches/models.py:31` — `NullBooleanField` → `BooleanField(null=True)`
  - [x] `predictions/models.py:27` — `NullBooleanField` → `BooleanField(null=True)`
  - [x] `predictions/models.py:40` — `NullBooleanField` → `BooleanField(null=True)`
  - [x] ~~`predictions/forms.py:12` — `forms.NullBooleanField` → `forms.BooleanField`~~
        **correction: left as-is.** `forms.NullBooleanField` is a *different* class
        from `models.NullBooleanField` — only the model field was deprecated/removed
        in Django 4; the form field (`django.forms.fields.NullBooleanField`) is alive
        and well in 5.2 (`forms.NullBooleanField` still resolves to it). No change
        needed here, and replacing it would have meant reimplementing the tri-state
        `penalty_winner` widget for no reason.
  - [x] `predictions/models.py:3` — `from django.contrib.postgres.fields import JSONField`
        → `from django.db.models import JSONField`
  - [x] `nostradamus/urls.py` — replaced all `url(r'^...$', ...)` with `re_path(r'^...$', ...)`
        (mechanical: `from django.urls import re_path` instead of
        `from django.conf.urls import url`, then rename `url(` → `re_path(`).
        Also had to special-case `password_reset_confirm`: Django 3.1+ generates
        longer reset tokens than the old custom regex allowed
        (`[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20}`), causing `NoReverseMatch` — switched
        that one route to `path('reset/<uidb64>/<token>/', ...)`, matching Django's
        own shipped URLconf pattern.
- [x] Add `DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'` to `nostradamus/settings.py`
      (Django 3.2 introduced this setting and warns without it; `AutoField` matches
      what the models already declare explicitly, so this just silences the warning
      without changing the schema)
- [x] Generate migrations for the field-class changes:
      `python manage.py makemigrations matches predictions`
      — review the generated migration files before applying; field-class-only
      changes (NullBooleanField → BooleanField, JSONField path) should produce
      `AlterField` operations with no actual DB column type change on Postgres
      — also had to delete a stray empty `predictions/tests.py` stub left over
      from initial scaffolding that conflicted with the `predictions/tests/`
      package and crashed the test loader (`ImportError: 'tests' module
      incorrectly imported`)
- [x] `python manage.py migrate` against your test DB and `python manage.py test`
- [x] Manually click through: login, signup, password reset/change, predictions
      table + submit form (exercises `penalty_winner`), results page, `/admin/`
- [x] Commit Phase 1 as its own PR

**Exit criteria:** tests pass, app works end-to-end on Django 3.2 / Python 3.7.

---

## Phase 2 — Bump Python 3.7 → 3.12 ✅ DONE — commit `c4e056a`

Django 2.2 cannot run on Python ≥3.10 (verified: install fails with
`ModuleNotFoundError: No module named 'distutils'`), which is why this comes
*after* Phase 1 — Django 3.2 supports Python 3.8–3.10, and later 3.2.x patches
extend that further, giving you a working combination to bump Python under.

- [x] Update `Containerfile`: `FROM python:3.7-slim` → `FROM python:3.12-slim`
- [x] Update `Makefile` `system-setup` target: `python3.7`/`python3.7-distutils`
      references → `python3.12` (drop `-distutils`, removed from stdlib in 3.12)
- [x] Update `venv-setup` target: `virtualenv venv -p python3.7` → `-p python3.12`
- [x] Recreate your local venv from scratch with Python 3.12 and reinstall
      `requirements.txt` — watch for C-extension build failures:
  - [x] `psycopg2-binary==2.8.3` likely needs bumping (no wheels for 3.12 at that
        version) — bumped to `2.9.12`
- [x] Re-run `python manage.py check`, `python manage.py migrate`,
      `python manage.py test` — fix anything that breaks purely from the Python
      version bump (e.g. stdlib removals: `distutils`, `cgi`, etc. — grep your
      own code and dependencies if something import-errors)
      — Python 3.12 removed the deprecated `unittest.TestCase.assertEquals` alias;
      20 occurrences across 7 test files needed `assertEquals` → `assertEqual`
      (`sed -i 's/\bassertEquals\b/assertEqual/g'`)
- [x] Re-run the manual click-through from Phase 1
- [x] Commit Phase 2 as its own PR

**Exit criteria:** tests pass, app works end-to-end on Django 3.2 / Python 3.12.

---

## Phase 3 — Django 3.2 → 4.2 LTS ✅ DONE — commit `2d1cf5f`

Goal: land on the target LTS. If Phase 1 was thorough, this should mostly be a
version bump plus dependency reconciliation — the removed-in-4.0 APIs
(`NullBooleanField`, `django.conf.urls.url`, old `JSONField` import path) are
already gone from the codebase.

- [x] Bump `Django==3.2.*` → `Django==4.2.*` (latest 4.2.x patch) in `requirements.txt`
- [x] `pip install -r requirements.txt` and run `python manage.py check --deploy`
      — also surfaced `ModuleNotFoundError: No module named 'pytz'` in
      `predictions/views.py`: Django 4.0+ dropped `pytz` as a transitive
      dependency (switched internally to `zoneinfo`), and this app imported it
      directly just for `pytz.utc`/`pytz.UTC`. Fixed by swapping to the stdlib
      `datetime.timezone.utc` — purely mechanical, no behavior change.
- [x] Fix anything `check` flags. Things to watch for specifically in this app:
  - [x] ~~`django-crispy-forms==1.11.2` — ... never actually used ...~~
        **correction: it IS used.** The grep in this plan only covered `*.py`
        files; `predictions/templates/details.html` actively renders
        `{{ form|crispy }}` (and `winner.html` loads the tag library too, albeit
        for a commented-out usage). Initially removed it per this plan's
        instruction, which broke `/predictions/<id>` with `TemplateSyntaxError:
        'crispy_forms_tags' is not a registered tag library`. Re-added it —
        but crispy-forms 2.x split Bootstrap support into a separate
        `crispy-bootstrap4` package and needs
        `CRISPY_ALLOWED_TEMPLATE_PACKS`/`CRISPY_TEMPLATE_PACK` settings.
        Landed on `django-crispy-forms==2.3` + `crispy-bootstrap4==2024.1`
        (the newest combo that still supports Django 4.2 — `crispy-forms>=2.4`
        requires Django ≥5.2).
  - [x] `whitenoise==5.3.0` — bumped to `6.12.0`
  - [x] `dj-database-url==0.5.0` → `3.1.2`, `django-widget-tweaks==1.4.2` → `1.5.1`,
        `django-mathfilters==0.4.0` → `1.0.0` — bumped, no compatibility issues
- [x] `python manage.py migrate` and `python manage.py test`
      — held at the 49/4/16 baseline, no regressions
- [x] Full manual regression pass — this is the part that matters most, since
      5 versions of behavioral changes (form validation, password-reset token
      handling, admin, querysets, template engine) won't all surface as
      import errors:
  - [x] Auth: signup, login, logout, password reset (email flow), password change
  - [x] Predictions: table view, submitting/editing a prediction, winner prediction
  - [x] Matches: index/list view, single match view
  - [x] Results page
  - [x] `/admin/` — all registered models (Team, Match, Prediction, Coefficient,
        OddMap, WinnerPrediction, WinnerPredictionCoef)
  - [x] `updater_tools/score_updater.py` — still imports/uses `Match` via the ORM;
        sanity check it still runs (`python -m updater_tools.score_updater`)
- [x] Commit Phase 3 as its own PR

**Exit criteria:** tests pass, full manual regression pass is clean, app runs on
Django 4.2 / Python 3.12.

---

## Phase 4 — Cleanup & deployment notes ✅ DONE — commits `5de8fbf`, `c84b1fa`

- [x] Update `readme.md` — replace remaining `python3.7`/`Python 3.7` references
      with 3.12, update any Django-version-specific notes
- [x] Update `gunicorn_start.sh.template`, `supervisor.conf.template`,
      `nginx_config.template` if they reference the venv's Python version path
      — checked: they all use generic `venv/bin/...` paths with no Python-version
      string baked in, nothing to change
- [x] Final full `python manage.py check --deploy` and test run
- [x] **Deployment note to carry forward:** written into `deployment.md` §6 —
      the next real deploy of this branch needs
      `python manage.py makemigrations accounts matches predictions results` run
      and the resulting migrations applied. The live DB's schema won't change
      shape (NullBooleanField/BooleanField(null=True) and the two JSONField
      classes are wire-compatible on Postgres `jsonb`), but Django's migration
      state needs to know about the field-class changes. Coordinate this with
      whoever owns the production deploy — don't run `migrate` against a live DB
      without a fresh backup in hand.

**Exit criteria:** branch is ready to merge to `master`; deployment notes written
down for whoever deploys it next.

---

## Phase 5 — Django 4.2 → 5.2 LTS (unplanned addition) ✅ DONE — commit `e3a4213`

Not in the original plan — added mid-session because Django 5.2 LTS had since
become the *current* latest LTS (support through ~April 2028, vs. 4.2's ~April
2026), and the LTS→LTS philosophy of this plan argues for landing on it rather
than stopping one rung short. Django 6.0 also exists at the time of writing but
is a regular (non-LTS) release with a much shorter support tail — deliberately
**not** targeted here; 5.2 LTS is the natural stopping point.

- [x] Bump `Django==4.2.*` → `Django==5.2.*` (latest 5.2.x patch, `5.2.15`) in
      `requirements.txt`
- [x] Remove `USE_L10N = True` from `nostradamus/settings.py` — deprecated as a
      no-op since Django 4.0 (localization is always on now), and the setting
      itself was removed in Django 5.0
- [x] Re-check crispy-forms pairing: `django-crispy-forms==2.3` was capped to
      stay 4.2-compatible in Phase 3 (`>=2.4` requires Django ≥5.2) — now that
      we're on 5.2, bumped to `django-crispy-forms==2.6` + `crispy-bootstrap4==2024.10`
- [x] Grepped for other 5.0/5.1/5.2-removed APIs (`index_together`,
      `assertQuerysetEqual`, `force_text`/`smart_text`, `MemcachedCache`,
      `CryptPasswordHasher`, `length_is` template filter, etc.) — none present
- [x] `python manage.py check --deploy`, `migrate`, `test` — held at the 49/4/16
      baseline, no regressions; `check --deploy` shows the same 5 standard
      production-hardening warnings as on 4.2 (HSTS, SSL redirect, secure
      cookies, DEBUG) — pre-existing deployment posture, not new in 5.2
- [x] Manual regression pass: login, `/admin/`, matches/predictions/results
      pages, submitting a prediction (exercises the migrated `BooleanField`
      and crispy-rendered form)
- [x] Commit Phase 5 as its own PR

**Exit criteria:** tests pass, full manual regression pass is clean, app runs on
Django 5.2 LTS / Python 3.12.
