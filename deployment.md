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

Enable the Podman socket (needed for `podman compose`):

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
    current/    → domain.com
    2018/       → 2018.domain.com
    caddy/
        Caddyfile
```

---

## 3. Configure environment files

Each version needs its own `.env`. Start from the example:

```bash
cp /srv/nostradamus/2018/.env.example /srv/nostradamus/2018/.env
```

Edit `/srv/nostradamus/2018/.env`:

```
SECRET_KEY=<generate with: python3 -c "import secrets; print(secrets.token_urlsafe(50))">
DEBUG=False
ALLOWED_HOSTS=2018.domain.com
DATABASE_URL=postgres://u_nostr:<db_password>@db:5432/db_nostr
```

> Replace `domain.com` with your actual domain throughout this guide.

---

## 4. Restore database snapshot (optional)

If you have a `.sql.gz` dump, place it in the version directory and reference it in `compose.yaml`:

```yaml
- ./db_nostr_backup.sql.gz:/docker-entrypoint-initdb.d/02_restore.sql.gz:ro
```

The Postgres container restores it automatically on first start. If the data volume already exists, it is skipped — use `podman compose down -v` first to wipe it.

---

## 5. Start the stacks

```bash
podman compose --project-name nostr-2018 \
    -f /srv/nostradamus/2018/compose.yaml up -d
```

On startup the web container runs `collectstatic` then launches gunicorn. Check logs:

```bash
podman logs nostr-2018-web-1
```

Expected output:

```
N static files copied to '/app/staticfiles'.
[INFO] Starting gunicorn 19.8.1
[INFO] Listening at: http://0.0.0.0:8000
```

### Port assignment

Each version binds gunicorn to a distinct `127.0.0.1` port:

| Version | Port |
|---------|------|
| current | `127.0.0.1:8000` |
| 2018    | `127.0.0.1:8018` |
| 2020    | `127.0.0.1:8020` |

---

## 6. Configure Caddy

```bash
mkdir -p /srv/nostradamus/caddy
```

Create `/srv/nostradamus/caddy/Caddyfile`:

```
2018.domain.com {
    reverse_proxy 127.0.0.1:8018
}

domain.com, www.domain.com {
    reverse_proxy 127.0.0.1:8000
}
```

Point Caddy at this file by editing `/etc/caddy/Caddyfile` — replace its contents with a single import:

```
import /srv/nostradamus/caddy/Caddyfile
```

Reload Caddy:

```bash
sudo systemctl reload caddy
```

Caddy issues and renews TLS certificates automatically via Let's Encrypt. Ports 80 and 443 must be open (done in step 1) and DNS A records for each subdomain must point at the server before reloading.

---

## 7. Auto-start containers on boot

Create a systemd user service for each stack. Example for the 2018 version:

```bash
mkdir -p ~/.config/systemd/user
```

Create `~/.config/systemd/user/nostr-2018.service`:

```ini
[Unit]
Description=Nostradamus 2018
After=default.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/srv/nostradamus/2018
ExecStart=/usr/bin/docker-compose --project-name nostr-2018 up -d
ExecStop=/usr/bin/docker-compose --project-name nostr-2018 down
TimeoutStartSec=300

[Install]
WantedBy=default.target
```

Enable and start:

```bash
systemctl --user daemon-reload
systemctl --user enable --now nostr-2018
```

Repeat for each additional version, changing the unit name, `WorkingDirectory`, and `--project-name`.

---

## 8. Create a Django superuser

```bash
podman exec -it nostr-2018-web-1 python manage.py createsuperuser
```

---

## 9. Adding a new historical version

1. Create a branch (e.g. `v2020`) with `compose.yaml` port set to `127.0.0.1:8020:8000`
2. Add a worktree: `git -C /srv/nostradamus/current worktree add /srv/nostradamus/2020 v2020`
3. Copy and edit `.env`: `cp /srv/nostradamus/2018/.env /srv/nostradamus/2020/.env`
4. Start the stack: `podman compose --project-name nostr-2020 -f /srv/nostradamus/2020/compose.yaml up -d`
5. Add a block to the Caddyfile and `sudo systemctl reload caddy`
6. Create a systemd unit as in step 7 and enable it

---

## Database operations

### Create a snapshot

```bash
podman exec nostr-2018-db-1 \
    pg_dump -U u_nostr db_nostr \
    | gzip > db_nostr_backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

### Restore into a running container

```bash
podman cp db_nostr_backup.sql.gz nostr-2018-db-1:/tmp/

podman exec -it nostr-2018-db-1 bash -c \
    "zcat /tmp/db_nostr_backup.sql.gz | psql -U u_nostr -d db_nostr"
```

### Restore on fresh volume (wipes existing data)

Update the `compose.yaml` volume mount to point at the dump file, then:

```bash
podman compose --project-name nostr-2018 down -v
podman compose --project-name nostr-2018 -f /srv/nostradamus/2018/compose.yaml up -d
```

---

## Troubleshooting

| Symptom | Check |
|---------|-------|
| Blank page, no CSS | `podman logs nostr-2018-web-1` — confirm `collectstatic` ran |
| 502 Bad Gateway | Gunicorn not running — check logs; confirm port in Caddyfile matches `compose.yaml` |
| TLS certificate not issued | DNS A record must exist before Caddy first starts; check `sudo journalctl -u caddy` |
| Container not starting after reboot | Confirm `loginctl enable-linger deploy` was run; check `systemctl --user status nostr-2018` |
| Port already in use | Another version's stack is using the same port — check port assignments in step 5 |
