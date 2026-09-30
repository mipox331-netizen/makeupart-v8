#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")/.."
set -a
. .env.production
set +a

mkdir -p backups
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
output="backups/makeupart_${timestamp}.sql.gz"

docker compose -f docker-compose.production.yml --env-file .env.production exec -T db \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" | gzip > "$output"

echo "Backup written to $output"
