# Deployment guide — Ubuntu 24.04

## 1. Initial server setup

### Create a dedicated user

```bash
adduser deploy
usermod -aG sudo deploy
```

Log in as the new user for all remaining steps:

```bash
su - deploy
```

### Install system packages

```bash
sudo apt update && sudo apt install -y \
    podman \
    docker-compose \
    git \
    ufw
```

> **Note:** On Ubuntu 24.04 the `docker-compose` package installs Compose v2 as a Podman compose backend. `podman compose` delegates to it automatically.

### Configure the firewall

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### Install Caddy

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
    | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
    | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install -y caddy
```

Verify Caddy is running:

```bash
sudo systemctl status caddy
```

### Enable rootless Podman to survive logout

By default, rootless containers stop when the user logs out. Enable linger so the user's systemd session starts at boot:

```bash
sudo loginctl enable-linger deploy
```

Enable the Podman socket:

```bash
systemctl --user enable --now podman.socket
```

---

## 2. Clone the repository

Use git worktrees so all versions share a single `.git` object store:

```bash
sudo mkdir -p /srv/nostradamus
sudo chown deploy:deploy /srv/nostradamus

git clone git@github.com:uncletoxa/nostradamus.git /srv/nostradamus/current
```

Add a worktree for each historical version:

```bash
git -C /srv/nostradamus/current worktree add /srv/nostradamus/2018 v2018
```

Final layout:

```
/srv/nostradamus/
    postgres/       ← shared database instance
    current/        → domain.com
    2018/           → 2018.domain.com
    caddy/
        Caddyfile
```

---

## 3. Start the shared PostgreSQL instance

All site versions share a single Postgres container. Each version gets its own database within it.

Create the postgres stack directory:

```bash
mkdir -p /srv/nostradamus/postgres
```

Create `/srv/nostradamus/postgres/compose.yaml`:

```yaml
services:
  db:
    image: docker.io/library/postgres:16
    hostname: postgres
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - db_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 10
    networks:
      - nostr_shared

networks:
  nostr_shared:
    name: nostr_shared

volumes:
  db_data:
```

Start it:

```bash
podman compose --project-name nostr-postgres \
    -f /srv/nostradamus/postgres/compose.yaml up -d
```

### Create a database for each version

Run once per version. For the 2018 version:

```bash
podman compose --project-name nostr-postgres \
    -f /srv/nostradamus/postgres/compose.yaml \
    exec db psql -U postgres \
    -c "CREATE USER u_nostr_2018 WITH PASSWORD 'nostr';" \
    -c "CREATE DATABASE db_nostr_2018 OWNER u_nostr_2018;" \
    -c "GRANT ALL PRIVILEGES ON DATABASE db_nostr_2018 TO u_nostr_2018;"
```

For the current version:

```bash
podman compose --project-name nostr-postgres \
    -f /srv/nostradamus/postgres/compose.yaml \
    exec db psql -U postgres \
    -c "CREATE USER u_nostr WITH PASSWORD 'nostr';" \
    -c "CREATE DATABASE db_nostr OWNER u_nostr;" \
    -c "GRANT ALL PRIVILEGES ON DATABASE db_nostr TO u_nostr;"
```

> The database password can be a simple string — the port is never exposed outside the `nostr_shared` network. `SECRET_KEY` in the app's `.env` is what must be kept strong and secret.

---

## 4. Configure environment files

Each version needs its own `.env`:

```bash
cp /srv/nostradamus/2018/.env.example /srv/nostradamus/2018/.env
```

Edit `/srv/nostradamus/2018/.env`:

```
SECRET_KEY=<generate with: `python3 -c "import secrets; print(secrets.token_urlsafe(50))`">
DEBUG=False
ALLOWED_HOSTS=2018.domain.com
DATABASE_URL=postgres://u_nostr_2018:nostr@postgres:5432/db_nostr_2018
```

> Replace `domain.com` with your actual domain throughout this guide.

---

## 5. Restore database snapshot (optional)

If you have a `.sql.gz` dump, restore it into the running Postgres container:

```bash
zcat db_nostr_2018_backup.sql.gz \
    | podman compose --project-name nostr-postgres \
        -f /srv/nostradamus/postgres/compose.yaml \
        exec -T db psql -U u_nostr_2018 -d db_nostr_2018
```

---

## 6. Start the app stacks

```bash
podman compose --project-name nostr-2018 \
    -f /srv/nostradamus/2018/compose.yaml up -d
```

On startup the web container runs `collectstatic` then launches gunicorn. Check logs:

```bash
podman compose --project-name nostr-2018 \
    -f /srv/nostradamus/2018/compose.yaml logs web
```

Expected output:

```
N static files copied to '/app/staticfiles'.
[INFO] Starting gunicorn 19.8.1
[INFO] Listening at: http://0.0.0.0:8000
```

### Port assignment

Each version binds gunicorn to a distinct `127.0.0.1` port:

| Version | Port | Database |
|---------|------|----------|
| current | `127.0.0.1:8000` | `db_nostr` |
| 2018    | `127.0.0.1:8018` | `db_nostr_2018` |
| 2020    | `127.0.0.1:8020` | `db_nostr_2020` |

---

## 7. Configure Caddy

```bash
mkdir -p /srv/nostradamus/caddy
```

Create `/srv/nostradamus/caddy/Caddyfile`. Only add a block for a domain once its app stack is actually running — Caddy will fail to obtain a TLS certificate (and log connection-refused errors) for any domain whose backend isn't listening yet:

```
2018.domain.com {
    reverse_proxy 127.0.0.1:8018
}

# Add once the current version's stack is deployed and listening on 127.0.0.1:8000:
# domain.com, www.domain.com {
#     reverse_proxy 127.0.0.1:8000
# }
```

Point Caddy at this file by editing `/etc/caddy/Caddyfile` — replace its contents with:

```
import /srv/nostradamus/caddy/Caddyfile
```

Reload Caddy:

```bash
sudo systemctl reload caddy
```

Caddy issues and renews TLS certificates automatically via Let's Encrypt. Ports 80 and 443 must be open and DNS A records for each subdomain must point at the server before reloading.

---

## 8. Auto-start on boot

Create a systemd user service for each stack. Start with the shared postgres — all app stacks depend on it:

```bash
mkdir -p ~/.config/systemd/user
```

Create `~/.config/systemd/user/nostr-postgres.service`:

```ini
[Unit]
Description=Nostradamus shared PostgreSQL
After=default.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/srv/nostradamus/postgres
ExecStart=/usr/bin/docker-compose --project-name nostr-postgres up -d
ExecStop=/usr/bin/docker-compose --project-name nostr-postgres down
TimeoutStartSec=60

[Install]
WantedBy=default.target
```

Create `~/.config/systemd/user/nostr-2018.service`:

```ini
[Unit]
Description=Nostradamus 2018
After=nostr-postgres.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/srv/nostradamus/2018
ExecStart=/usr/bin/docker-compose --project-name nostr-2018 up -d
ExecStop=/usr/bin/docker-compose --project-name nostr-2018 down
TimeoutStartSec=120

[Install]
WantedBy=default.target
```

Enable all services:

```bash
systemctl --user daemon-reload
systemctl --user enable --now nostr-postgres
systemctl --user enable --now nostr-2018
```

---

## 9. Create a Django superuser

```bash
podman compose --project-name nostr-2018 \
    -f /srv/nostradamus/2018/compose.yaml \
    exec web python manage.py createsuperuser
```

---

## 10. Adding a new historical version

1. Create branch `v20YY` with `compose.yaml` port set to `127.0.0.1:80YY:8000` and network set to `nostr_shared` (external)
2. Add a worktree: `git -C /srv/nostradamus/current worktree add /srv/nostradamus/20YY v20YY`
3. Create the database: run the `psql` command from step 3 with `u_nostr_20YY` / `db_nostr_20YY`
4. Copy and edit `.env`: `cp /srv/nostradamus/2018/.env /srv/nostradamus/20YY/.env`
5. Start the stack: `podman compose --project-name nostr-20YY -f /srv/nostradamus/20YY/compose.yaml up -d`
6. Add a block to the Caddyfile and `sudo systemctl reload caddy`
7. Create a systemd unit as in step 8 with `After=nostr-postgres.service`

---

## Database operations

### Create a snapshot

```bash
podman compose --project-name nostr-postgres \
    -f /srv/nostradamus/postgres/compose.yaml \
    exec -T db pg_dump -U u_nostr_2018 db_nostr_2018 \
    | gzip > db_nostr_2018_backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

### Restore into a running instance

```bash
zcat db_nostr_2018_backup.sql.gz \
    | podman compose --project-name nostr-postgres \
        -f /srv/nostradamus/postgres/compose.yaml \
        exec -T db psql -U u_nostr_2018 -d db_nostr_2018
```

---

## Troubleshooting

| Symptom | Check |
|---------|-------|
| Blank page, no CSS | `podman compose --project-name nostr-2018 -f /srv/nostradamus/2018/compose.yaml logs web` — confirm `collectstatic` ran |
| 502 Bad Gateway | Gunicorn not running — check logs; confirm port in Caddyfile matches `compose.yaml` |
| Database connection refused | Shared postgres not running — `podman ps` and `systemctl --user status nostr-postgres` |
| TLS certificate not issued | DNS A record must exist before Caddy first starts; check `sudo journalctl -u caddy` |
| Container not starting after reboot | Confirm `loginctl enable-linger deploy` was run; check `systemctl --user status nostr-2018` |
| Port already in use | Another version's stack is using the same port — check port assignments in step 6 |
