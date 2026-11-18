#!/bin/bash
# Runs once, on the first start of the primary (docker-entrypoint-initdb.d).
# Creates the replication role + a physical slot so the replica never misses WAL.
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE ROLE ${REPLICATION_USER} WITH REPLICATION LOGIN PASSWORD '${REPLICATION_PASSWORD}';
    SELECT pg_create_physical_replication_slot('${REPLICATION_SLOT:-replica_1}');
EOSQL

# "all" in pg_hba.conf does NOT match replication connections - it needs its own line
echo "host replication ${REPLICATION_USER} all scram-sha-256" >> "$PGDATA/pg_hba.conf"
