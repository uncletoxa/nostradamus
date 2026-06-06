# Deployment

## Podman Compose (recommended)

### Prerequisites

- [Podman](https://podman.io/getting-started/installation) with the socket activated
- `podman-compose` or `docker-compose` CLI

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
| `DEBUG` | `False` for production |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hostnames (e.g. `2018.example.com`) |
| `DATABASE_URL` | `postgres://u_nostr:<password>@db:5432/db_nostr` — use `db` as the host when running via compose |

### 2. Start the stack

```bash
podman compose --project-name nostr-2018 up -d
```

The `--project-name` flag is required when running multiple version stacks on the same host to avoid container and volume name collisions.

On startup the container automatically runs `collectstatic` before gunicorn starts.

This starts two services:
- **db** — PostgreSQL 16 (no host port; reachable only inside the compose network)
- **web** — gunicorn on `127.0.0.1:8018`, 2 workers

### 3. Create a superuser

```bash
podman exec -it nostr-2018-web-1 python manage.py createsuperuser
```

---

## Multi-version subdomain hosting

To serve multiple historical versions alongside the current site, each version runs as an independent Podman Compose stack behind a shared Caddy reverse proxy.

### Host layout

Use git worktrees so all versions share a single `.git` object store:

```bash
git clone git@github.com:uncletoxa/nostradamus.git /srv/nostradamus/current
git -C /srv/nostradamus/current worktree add /srv/nostradamus/2018 v2018
```

Each version directory needs its own `.env`:

```
/srv/nostradamus/
    current/    → domain.com          (port 8000)
    2018/       → 2018.domain.com     (port 8018)
    caddy/
        Caddyfile
```

### Port assignment

Each version's `compose.yaml` binds gunicorn to a distinct localhost port so Caddy can reach it:

| Version | Port |
|---------|------|
| current | `127.0.0.1:8000:8000` |
| 2018    | `127.0.0.1:8018:8000` |
| 2020    | `127.0.0.1:8020:8000` |

### Starting all stacks

```bash
podman compose --project-name nostr-current -f /srv/nostradamus/current/compose.yaml up -d
podman compose --project-name nostr-2018   -f /srv/nostradamus/2018/compose.yaml   up -d
```

### Caddy reverse proxy

Install Caddy on the host and create `/srv/nostradamus/caddy/Caddyfile`:

```
2018.domain.com {
    reverse_proxy 127.0.0.1:8018
}

domain.com, www.domain.com {
    reverse_proxy 127.0.0.1:8000
}
```

Caddy issues and renews TLS certificates automatically via Let's Encrypt. Reload after any Caddyfile change:

```bash
systemctl reload caddy
```

### Adding a new historical version

1. Create the branch with the port set to `127.0.0.1:80YY:8000` in `compose.yaml`
2. Add a worktree: `git -C /srv/nostradamus/current worktree add /srv/nostradamus/20YY v20YY`
3. Copy and edit `.env`
4. Start the stack: `podman compose --project-name nostr-20YY -f /srv/nostradamus/20YY/compose.yaml up -d`
5. Add a block to the Caddyfile and `systemctl reload caddy`

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
podman compose --project-name nostr-2018 up -d
```

### Option B — into a running container

```bash
podman cp db_nostr_backup.sql.gz nostr-2018-db-1:/tmp/

podman exec -it nostr-2018-db-1 bash -c \
  "zcat /tmp/db_nostr_backup.sql.gz | psql -U u_nostr -d db_nostr"
```

### Creating a snapshot

```bash
podman exec nostr-2018-db-1 \
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
