# Migrating a hosted instance back into code

Guide for turning a running (and possibly undocumented) deployment on a remote
host into a reproducible, version-controlled, containerized setup — e.g. to
preserve an old yearly instance of this app as a historical branch.

This was done once for the 2018 instance (`v2018` branch). Repeat these steps
for any other year/instance you want to recover.

## 1. Explore the remote host

SSH in and find where the app actually lives — it's rarely where you'd guess:

```bash
ssh <host>
ls ~                                    # home dir often has the project + helper scripts
cat ~/gunicorn_start.sh                 # reveals the project path, venv path, socket
ls ~/<project>/<project>/               # Django project root
```

Things to note down:
- Project directory path and Python version (`~/.../venv/bin/python --version`)
- Web server / process manager config (`gunicorn_start.sh`, `nginx_config`, supervisor conf)
- Database name, user, and how it's referenced (`DATABASE_URL` in `.env`)

## 2. Recover the secrets / config

Look for the `.env` file (or whatever `python-decouple`/`dj-database-url` reads):

```bash
find ~/<project> -maxdepth 3 -iname '*.env*'
cat ~/<project>/<project>/.env
```

This gives you `SECRET_KEY`, `ALLOWED_HOSTS`, `DATABASE_URL`, and any
service-specific tokens. You won't reuse these values for the migrated copy
(generate fresh secrets), but `DATABASE_URL` tells you the DB name/user, and
`ALLOWED_HOSTS` confirms the domain that was live at the time.

## 3. Identify the exact code version

The deployed code is very likely behind the latest `master` and may not match
any branch exactly. Compare commit logs:

```bash
ssh <host> "cd ~/<project>/<project> && git log --oneline" | head -20
git log --oneline <candidate-branch> | head -20
```

Look for the closest matching commit — the deployed HEAD might not exist in
your local repo at all (e.g. an unpushed "merge with prod" commit), but an
old branch's tip is often close enough. **Verify by comparing schema-sensitive
code**, not just commit messages — e.g. check that a model's fields match the
actual DB columns (see step 6). That's a much stronger signal than commit
proximity.

```bash
git show <branch>:path/to/models.py | grep -A5 "class ModelName"
```

Once you've found the right point, check it out into a dedicated branch:

```bash
git checkout -b v<year>
git checkout origin/<candidate-branch> -- .
git add -A && git commit -m "v<year>: snapshot of the deployed <year> system"
```

## 4. Get a database snapshot

Prefer an existing backup on the host if one exists (check for `*.sql*` files
in the project directory — they're often dropped there by cron jobs). Otherwise
take a fresh one:

```bash
ssh <host> "pg_dump -U <db_user> <db_name> | gzip" > db_backup.sql.gz
```

Keep this **out of git** — it contains real user data (emails, password
hashes, personal predictions, etc). Add `*.sql.gz` to `.gitignore`.

## 5. Containerize it

Set up `compose.yaml` + `Containerfile` (see this repo's for a working
example). Key points that tripped us up:

- **Image names need a full registry path** on hosts without
  `unqualified-search-registries` configured: use `docker.io/library/postgres:16`,
  not `postgres:16`.
- **Restoring a dump via `docker-entrypoint-initdb.d/`**: the postgres image
  creates `POSTGRES_USER` as the superuser. If your dump references a
  `postgres` role (common in `REVOKE ... FROM postgres` statements from
  pg_dump), either keep `POSTGRES_USER=postgres` and create your app's DB user
  via an init script that runs *before* the restore (`01_create_user.sql`,
  `02_restore.sql.gz` — they run in filename order), or the restore will abort
  partway through.
- **Host port conflicts**: if the host already runs Postgres on 5432, map the
  container to a different host port (e.g. `5433:5432`).
- **`depends_on: condition: service_healthy`** isn't supported by older
  `podman-compose` — use the plain list form `depends_on: [db]` instead.
- **`STATIC_ROOT = os.path.expanduser('~/staticfiles/')`**: set `ENV HOME=/app`
  in the Containerfile so this resolves predictably inside the container.

## 6. Restore and verify against the code

Bring the stack up and load the dump (see `deployment.md` → "Restoring a
database snapshot"). Then load the homepage. Schema mismatches between the old
DB and the checked-out code surface immediately as `ProgrammingError: column
... does not exist`.

When that happens, compare the model to the actual table:

```bash
psql "<connection-string>" -c '\d <table_name>'
git show <branch>:<app>/models.py | grep -A5 "class <ModelName>"
```

If the column names match a *different* branch's model than the one you
checked out, that's a strong signal you picked the wrong commit — go back to
step 3 and try an earlier/later candidate.

## 7. Recover assets that aren't in git

Old deployments often have static files (logos, fonts, one-off images) that
were uploaded directly to the server and never committed. Diff the host
against your checkout:

```bash
ssh <host> "find ~/<project>/<project>/static/ -type f" > /tmp/host_static.txt
find ./static/ -type f > /tmp/local_static.txt
# compare basenames, then scp over whatever's missing
scp "<host>:~/<project>/<project>/static/img/missing.jpg" ./static/img/
```

Grep the templates for any `{% static '...' %}` references that 404 to find
what's actually missing and in use (vs. orphaned files you can skip).

## 8. Commit the snapshot

```bash
git add -A
git commit -m "v<year>: historical snapshot of the deployed <year> system with podman compose setup"
git push origin v<year>
```

Keep `.env`, `*.sql.gz`, and any other generated/sensitive artifacts out of
the commit — only the code, container setup, and recovered static assets
belong in the historical branch.
