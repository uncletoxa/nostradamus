# Deployment guide — Ubuntu 24.04

This guide covers deploying the live site (this branch, served at `domain.com`) via Podman Compose, plus how to host historical version snapshots (e.g. `2018.domain.com`) alongside it on the same server.

Every checkout — live or historical — lives in a directory named after its year (e.g. `2026/`, `2018/`). Nothing in the directory/project naming marks one as "current"; only the Caddy routing does, by binding the live version's block to the root domain instead of `20YY.domain.com`.

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

Clone this branch into a directory named after its year — that's the live checkout. If you also want to host historical versions, add them as git worktrees so everything shares a single `.git` object store:

```bash
sudo mkdir -p /srv/nostradamus
sudo chown deploy:deploy /srv/nostradamus

git clone git@github.com:uncletoxa/nostradamus.git /srv/nostradamus/2026
git -C /srv/nostradamus/2026 worktree add /srv/nostradamus/2018 v2018
```

Final layout:

```
/srv/nostradamus/
    postgres/       ← shared database instance
    2026/           → domain.com            (live version — this branch)
    2018/           → 2018.domain.com       (historical snapshot, optional)
    caddy/
        Caddyfile
```

> The live checkout's directory, project name, and systemd unit are all named after its year just like any historical one — e.g. `2026`/`nostr-2026`. The only thing that makes it "current" is the Caddy block (step 7) binding it to the root domain instead of `20YY.domain.com`. When a new season's branch takes over as live, deploy it like a historical version, then move the root-domain Caddy block to point at its port and demote the old live version to a `20YY.domain.com` block.

If you are not hosting any historical versions, skip the `worktree add` step and the `2018`-specific commands below.

---

## 3. Start the shared PostgreSQL instance

All site versions — current and historical — share a single Postgres container. Each gets its own database within it.

The compose file for this shared instance is version-controlled at `docker/postgres-shared/compose.yaml` (it's infrastructure shared by every version, not specific to any one of them — kept here rather than duplicated per branch). Copy it out to its own directory:

```bash
mkdir -p /srv/nostradamus/postgres
cp /srv/nostradamus/2026/docker/postgres-shared/compose.yaml /srv/nostradamus/postgres/compose.yaml
```

> The `aliases` entry in that file is what makes the container resolvable as `postgres` from other compose stacks on the `nostr_shared` network — a `hostname:` field alone only sets the container's own internal hostname and does not register a network-wide DNS entry.
>
> To pick up future changes to this file, `git pull` in `/srv/nostradamus/2026` (the live checkout) and re-copy it, then recreate the container with `up -d --force-recreate`.

Start it:

```bash
podman compose --project-name nostr-postgres \
    -f /srv/nostradamus/postgres/compose.yaml up -d
```

### Create a database for each version

Run once per version. For the live site (2026):

```bash
podman compose --project-name nostr-postgres \
    -f /srv/nostradamus/postgres/compose.yaml \
    exec db psql -U postgres \
    -c "CREATE USER u_nostr_2026 WITH PASSWORD 'nostr';" \
    -c "CREATE DATABASE db_nostr_2026 OWNER u_nostr_2026;" \
    -c "GRANT ALL PRIVILEGES ON DATABASE db_nostr_2026 TO u_nostr_2026;"
```

For the 2018 historical version (if hosting it):

```bash
podman compose --project-name nostr-postgres \
    -f /srv/nostradamus/postgres/compose.yaml \
    exec db psql -U postgres \
    -c "CREATE USER u_nostr_2018 WITH PASSWORD 'nostr';" \
    -c "CREATE DATABASE db_nostr_2018 OWNER u_nostr_2018;" \
    -c "GRANT ALL PRIVILEGES ON DATABASE db_nostr_2018 TO u_nostr_2018;"
```

> The database password can be a simple string — the port is never exposed outside the `nostr_shared` network. `SECRET_KEY` in the app's `.env` is what must be kept strong and secret.

---

## 4. Configure environment files

Each version needs its own `.env`. For the live site (2026):

```bash
cp /srv/nostradamus/2026/.env.example /srv/nostradamus/2026/.env
```

Edit `/srv/nostradamus/2026/.env`:

```
SECRET_KEY=<generate with: `python3 -c "import secrets; print(secrets.token_urlsafe(50))`">
DEBUG=False
ALLOWED_HOSTS=domain.com,www.domain.com
DATABASE_URL=postgres://u_nostr_2026:nostr@postgres:5432/db_nostr_2026
```

> Replace `domain.com` with your actual domain throughout this guide.

For the 2018 version (if hosting it), repeat with `ALLOWED_HOSTS=2018.domain.com` and the `u_nostr_2018` / `db_nostr_2018` credentials from step 3.

---

## 5. Restore database snapshot (optional)

If you have a `.sql.gz` dump, restore it into the running shared Postgres container:

```bash
zcat db_nostr_2026_backup.sql.gz \
    | podman compose --project-name nostr-postgres \
        -f /srv/nostradamus/postgres/compose.yaml \
        exec -T db psql -U u_nostr_2026 -d db_nostr_2026
```

---

## 6. Start the app stacks

> **Deploying the Django 2.2 → 5.2 upgrade branch:** migrations aren't tracked in
> git for this project — they're generated fresh per deploy. Before starting the
> stack on this branch for the first time, take a fresh backup of the live DB,
> then run `python manage.py makemigrations accounts matches predictions results`
> and apply the result with `migrate`. The Postgres schema itself won't change
> shape (`NullBooleanField` / `BooleanField(null=True)` and the old
> `django.contrib.postgres.fields.JSONField` / `django.db.models.JSONField` are
> wire-compatible on `jsonb`), but Django's migration state needs to be told
> about the field-class changes made during the upgrade. Coordinate the timing
> with whoever owns the deploy — don't run `migrate` against a live DB without a
> fresh backup in hand.

```bash
podman compose --project-name nostr-2026 \
    -f /srv/nostradamus/2026/compose.yaml up -d
```

On startup the web container compiles translation catalogs, runs `collectstatic`, then launches gunicorn. Check logs:

```bash
podman compose --project-name nostr-2026 \
    -f /srv/nostradamus/2026/compose.yaml logs web
```

Expected output:

```
processing file django.po in /app/locale/ru/LC_MESSAGES
N static files copied to '/app/staticfiles'.
[INFO] Starting gunicorn 22.0.0
[INFO] Listening at: http://0.0.0.0:8000
```

If hosting the 2018 version too:

```bash
podman compose --project-name nostr-2018 \
    -f /srv/nostradamus/2018/compose.yaml up -d
```

### Port assignment

Each version binds gunicorn to a distinct `127.0.0.1` port:

| Version | Port | Database |
|---------|------|----------|
| 2026 (live) | `127.0.0.1:8000` | `db_nostr_2026` |
| 2018    | `127.0.0.1:8018` | `db_nostr_2018` |
| 2020    | `127.0.0.1:8020` | `db_nostr_2020` |

> Port `8000` belongs to whichever version is currently live, regardless of its year — it's what the root-domain Caddy block points at. When promoting a new year to live, give it port `8000` and move the previous live version to its own `80YY` slot.

---

## 7. Configure Caddy

```bash
mkdir -p /srv/nostradamus/caddy
```

Create `/srv/nostradamus/caddy/Caddyfile`. Only add a block for a domain once its app stack is actually running — Caddy will fail to obtain a TLS certificate (and log connection-refused errors) for any domain whose backend isn't listening yet:

```
# Live version (currently 2026) — bound to the root domain, not <year>.domain.com:
domain.com, www.domain.com {
    reverse_proxy 127.0.0.1:8000
}

# Add once the 2018 stack is deployed and listening on 127.0.0.1:8018:
# 2018.domain.com {
#     reverse_proxy 127.0.0.1:8018
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

Caddy issues and renews TLS certificates automatically via Let's Encrypt. Ports 80 and 443 must be open and DNS A records for each domain must point at the server before reloading.

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

Create `~/.config/systemd/user/nostr-2026.service`:

```ini
[Unit]
Description=Nostradamus 2026 (live)
After=nostr-postgres.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/srv/nostradamus/2026
ExecStart=/usr/bin/docker-compose --project-name nostr-2026 up -d
ExecStop=/usr/bin/docker-compose --project-name nostr-2026 down
TimeoutStartSec=120

[Install]
WantedBy=default.target
```

Enable the services:

```bash
systemctl --user daemon-reload
systemctl --user enable --now nostr-postgres
systemctl --user enable --now nostr-2026
```

Repeat the unit creation for `nostr-2018` (and any other historical version) with `After=nostr-postgres.service`, the matching `WorkingDirectory`, and `--project-name`.

---

## 9. Create a Django superuser

```bash
podman compose --project-name nostr-2026 \
    -f /srv/nostradamus/2026/compose.yaml \
    exec web python manage.py createsuperuser
```

---

## 10. Adding a historical version

1. Create branch `v20YY` with `compose.yaml` port set to `127.0.0.1:80YY:8000` and network set to `nostr_shared` (external)
2. Add a worktree: `git -C /srv/nostradamus/2026 worktree add /srv/nostradamus/20YY v20YY`
3. Create the database: run the `psql` command from step 3 with `u_nostr_20YY` / `db_nostr_20YY`
4. Copy and edit `.env`: `cp /srv/nostradamus/2026/.env /srv/nostradamus/20YY/.env`, then set `ALLOWED_HOSTS` and `DATABASE_URL`
5. Start the stack: `podman compose --project-name nostr-20YY -f /srv/nostradamus/20YY/compose.yaml up -d`
6. Add a block to the Caddyfile and `sudo systemctl reload caddy`
7. Create a systemd unit as in step 8 with `After=nostr-postgres.service`

---

## Routine deploy

To push a code update to the live site:

```bash
cd /srv/nostradamus/2026
git pull
podman compose --project-name nostr-2026 -f compose.yaml up -d --build
```

The container entrypoint runs `compilemessages` and `collectstatic` automatically on every start, so no extra steps are needed after a build. Check logs to confirm a clean startup:

```bash
podman compose --project-name nostr-2026 -f compose.yaml logs --tail=20 web
```

> **Translations note:** `.mo` compiled translation files are not tracked in git. They are compiled from the `.po` source files inside the container at startup. If you add or edit translations locally, commit only the `.po` file — the `.mo` is regenerated automatically on the next deploy.

---

## Database operations

### Create a snapshot

```bash
podman compose --project-name nostr-postgres \
    -f /srv/nostradamus/postgres/compose.yaml \
    exec -T db pg_dump -U u_nostr_2026 db_nostr_2026 \
    | gzip > db_nostr_2026_backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

Adjust the user/database names to back up a different version (e.g. `u_nostr_2018` / `db_nostr_2018`).

### Restore into a running instance

```bash
zcat db_nostr_2026_backup.sql.gz \
    | podman compose --project-name nostr-postgres \
        -f /srv/nostradamus/postgres/compose.yaml \
        exec -T db psql -U u_nostr_2026 -d db_nostr_2026
```

---

## Troubleshooting

| Symptom | Check |
|---------|-------|
| Blank page, no CSS | `podman compose --project-name nostr-2026 -f /srv/nostradamus/2026/compose.yaml logs web` — confirm `compilemessages` and `collectstatic` ran |
| 502 Bad Gateway | Gunicorn not running — check logs; confirm port in Caddyfile matches `compose.yaml` |
| Database connection refused | Shared postgres not running — `podman ps` and `systemctl --user status nostr-postgres` |
| TLS certificate not issued | DNS A record must exist before Caddy first starts; check `sudo journalctl -u caddy` |
| Container not starting after reboot | Confirm `loginctl enable-linger deploy` was run; check `systemctl --user status nostr-2026` |
| Port already in use | Another version's stack is using the same port — check port assignments in step 6 |
