#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env}"
MOCK_CSV="${MOCK_CSV:-$ROOT_DIR/data/leads_mock.csv}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-postgres-hdd}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Arquivo .env não encontrado: $ENV_FILE" >&2
  exit 1
fi

if [[ ! -f "$MOCK_CSV" ]]; then
  echo "CSV mock não encontrado: $MOCK_CSV" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

: "${POSTGRES_DB:?POSTGRES_DB não definido no .env}"
: "${POSTGRES_USER:?POSTGRES_USER não definido no .env}"

docker exec "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=1 -Atc \
  "SELECT 1 FROM pg_database WHERE datname = '$POSTGRES_DB';" | grep -q 1 \
  || docker exec "$POSTGRES_CONTAINER" createdb -U "$POSTGRES_USER" "$POSTGRES_DB"

docker cp "$MOCK_CSV" "$POSTGRES_CONTAINER:/tmp/leads_mock.csv"

docker exec -i "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 <<'SQL'
CREATE TABLE IF NOT EXISTS leads (
    id BIGSERIAL PRIMARY KEY,
    full_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT,
    course_interest TEXT,
    duration_interest TEXT,
    opt_in_whatsapp BOOLEAN NOT NULL DEFAULT true,
    sale_started BOOLEAN NOT NULL DEFAULT false,
    enrollment_done BOOLEAN NOT NULL DEFAULT false,
    already_sent BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

TRUNCATE TABLE leads RESTART IDENTITY;

\copy leads (full_name, phone, email, course_interest, duration_interest, opt_in_whatsapp, sale_started, enrollment_done, already_sent, created_at) FROM '/tmp/leads_mock.csv' WITH (FORMAT csv, HEADER true);
SQL

docker exec "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc \
  "SELECT 'leads_total=' || count(*) || ' eligible=' || count(*) FILTER (WHERE opt_in_whatsapp AND NOT sale_started AND NOT enrollment_done AND NOT already_sent) FROM leads;"
