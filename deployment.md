# Deployment

## Podman Compose (recommended)

### Prerequisites

- [Podman](https://podman.io/getting-started/installation) with the socket activated
- `docker-compose` CLI (used as the compose backend)

Enable the Podman socket for your user:
```bash
systemctl --user enable --now podman.socket
```

### 1. Configure environment

Copy `.env.example` to `.env` and fill in the values:

```bash
cp .env.example .env
```

| Variable | Description |
|---|---|
| `SECRET_KEY` | Django secret key (generate with `python -c "import secrets; print(secrets.token_urlsafe(50))"`) |
| `DEBUG` | `True` for development, `False` for production |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hostnames |
| `DATABASE_URL` | `postgres://u_nostr:<password>@db:5432/db_nostr` — use `db` as the host when running via compose |

### 2. Start the stack

```bash
podman compose up -d
```

This starts two services:
- **db** — PostgreSQL 16 on port 5433
- **web** — Django dev server on port 8000

The app is available at http://localhost:8000.

### 3. Create a superuser

```bash
podman exec -it nostradamus-web-1 python manage.py createsuperuser
```

---

## Restoring a database snapshot

If you have a `.sql.gz` dump (created with `pg_dump`), you can restore it in two ways:

### Option A — on first run (recommended for fresh installs)

Place the dump file in the project root and reference it in `compose.yaml` as an init script. The PostgreSQL container automatically restores any `.sql` or `.sql.gz` files placed in `/docker-entrypoint-initdb.d/` on first start (only if the data volume is empty).

The `compose.yaml` in this repo already has this wired up — just drop your dump as `db_nostr_backup.sql.gz` and update the filename in the volume mount:

```yaml
- ./db_nostr_backup.sql.gz:/docker-entrypoint-initdb.d/02_restore.sql.gz:ro
```

Then start fresh:

```bash
podman compose down -v   # removes the data volume
podman compose up -d
```

### Option B — into a running container

```bash
# Copy the dump into the container
podman cp db_nostr_backup.sql.gz nostradamus-db-1:/tmp/

# Restore it
podman exec -it nostradamus-db-1 bash -c \
  "zcat /tmp/db_nostr_backup.sql.gz | psql -U u_nostr -d db_nostr"
```

### Creating a snapshot

To back up the running database:

```bash
podman exec nostradamus-db-1 \
  pg_dump -U u_nostr db_nostr | gzip > db_nostr_backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

---

## Traditional deployment (bare metal)

See the `Makefile` for the full automated setup. Requires Ubuntu with Python 3.7, PostgreSQL, Nginx, and Supervisor.

```bash
make domain="example.com" db_password="your_db_password"
```

Steps performed by `make`:
1. Installs system packages (Python 3.7, PostgreSQL, Nginx, Supervisor)
2. Creates the database user and database
3. Creates a virtualenv and installs Python dependencies
4. Runs Django migrations and collects static files
5. Configures Gunicorn via Supervisor
6. Configures Nginx and issues a Let's Encrypt certificate

To clean up everything:
```bash
make clean -i
```
