# Nostradamus

Simple Django app for a predictions competition. Includes accounts management, predictions, matches, results tracker, and odds scraper.

## Local development

### Prerequisites

- [Podman](https://podman.io/getting-started/installation) with compose support, **or** Python 3.12 + PostgreSQL running locally

### Option A — Podman Compose (recommended)

No local Python or Postgres install needed. The app's `compose.yaml` joins an external `nostr_shared` network (the same pattern used in production to share one Postgres instance across site versions — see [deployment.md](deployment.md)), so for local use create that network and a local Postgres container once:

```bash
podman network create nostr_shared
podman run -d --name local-postgres \
    --network nostr_shared --network-alias postgres \
    -e POSTGRES_USER=u_nostr -e POSTGRES_PASSWORD=nostr -e POSTGRES_DB=db_nostr \
    docker.io/library/postgres:16
```

```bash
cp .env.example .env
# Edit .env — set SECRET_KEY; DATABASE_URL can stay as
# postgres://u_nostr:nostr@postgres:5432/db_nostr
```

Start the stack:

```bash
podman compose --project-name nostr-dev up --build
```

The app is available at http://localhost:8000.

Run Django management commands against the running container:

```bash
podman compose --project-name nostr-dev exec web python manage.py createsuperuser
podman compose --project-name nostr-dev exec web python manage.py migrate
podman compose --project-name nostr-dev exec web python manage.py shell
```

Stop and remove the app container:

```bash
podman compose --project-name nostr-dev down
```

Remove the local Postgres and network entirely:

```bash
podman rm -f local-postgres
podman network rm nostr_shared
```

### Option B — virtualenv + local Postgres

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create the database and user in Postgres, then:

```bash
cp .env.example .env
# Edit .env — set SECRET_KEY and DATABASE_URL to point at your local Postgres
# (use `localhost` as the host, not `postgres`)
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
| `DATABASE_URL` | `postgres://u_nostr:<password>@postgres:5432/db_nostr` — use `postgres` as the host with compose (see Option A), `localhost` with a local Postgres |

## Production deployment

See [deployment.md](deployment.md) for the full Podman Compose production setup, multi-version subdomain hosting, Caddy configuration, and database backup/restore procedures.
