#!/bin/bash
set -e

COMPOSE_FILE="compose.local.yaml"
DUMP_FILE="/tmp/nostr_prod_dump.sql"

echo "==> Dumping production database..."
/usr/bin/ssh nostradamus \
    "podman exec nostr-postgres_db_1 pg_dump -U postgres -d db_nostr_2026 --no-owner --no-privileges" \
    > "$DUMP_FILE"

echo "==> Resetting local database..."
docker compose -f "$COMPOSE_FILE" exec -T db \
    psql -U postgres -c "DROP DATABASE IF EXISTS db_nostr_2026 WITH (FORCE);"
docker compose -f "$COMPOSE_FILE" exec -T db \
    psql -U postgres -c "CREATE DATABASE db_nostr_2026 OWNER u_nostr_2026;"

echo "==> Restoring dump..."
docker compose -f "$COMPOSE_FILE" exec -T db \
    psql -U postgres -d db_nostr_2026 < "$DUMP_FILE"

rm "$DUMP_FILE"
echo "==> Done. Local DB is now a copy of production."
