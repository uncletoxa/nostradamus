# Nostradamus

Simple Django app for a predictions competition. Includes accounts management, predictions, matches, results tracker, and odds scraper.

## Local development

### Prerequisites

- [Podman](https://podman.io/getting-started/installation) with compose support, **or** Python 3.7 + PostgreSQL running locally

### Option A — Podman Compose (recommended)

No local Python or Postgres install needed.

```bash
cp .env.example .env
# Edit .env — set SECRET_KEY, leave other values as-is for local use
```

Start the stack:

```bash
podman compose --project-name nostr-dev up --build
```

The app is available at http://localhost:8018.

On first start with a DB dump in the project root, the database is restored automatically (see `compose.yaml` for the mount). To start with an empty database instead, remove the `02_restore.sql.gz` volume mount from `compose.yaml`.

Run Django management commands against the running container:

```bash
podman exec -it nostr-dev-web-1 python manage.py createsuperuser
podman exec -it nostr-dev-web-1 python manage.py migrate
podman exec -it nostr-dev-web-1 python manage.py shell
```

Stop and remove containers (keep DB data):

```bash
podman compose --project-name nostr-dev down
```

Wipe everything including the database volume:

```bash
podman compose --project-name nostr-dev down -v
```

### Option B — virtualenv + local Postgres

```bash
python3.7 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create the database and user in Postgres, then:

```bash
cp .env.example .env
# Edit .env — set SECRET_KEY and DATABASE_URL to point at your local Postgres
```

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py runserver
```

The app is available at http://localhost:8000.

## Environment variables

| Variable | Description |
|---|---|
| `SECRET_KEY` | Django secret key — generate with `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DEBUG` | `False` in production; you can set `True` locally for the Django debug toolbar and detailed error pages |
| `ALLOWED_HOSTS` | Comma-separated hostnames (e.g. `localhost,127.0.0.1`) |
| `DATABASE_URL` | `postgres://u_nostr:<password>@db:5432/db_nostr` — use `db` as the host with compose, `localhost` with a local Postgres |

## Production deployment

See [deployment.md](deployment.md) for the full Podman Compose production setup, multi-version subdomain hosting, Caddy configuration, and database backup/restore procedures.
