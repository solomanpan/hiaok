#!/bin/sh
# Streaming replica: clone the primary once with pg_basebackup (-R writes standby.signal +
# primary_conninfo), then run as a hot standby (read-only).
set -e

if [ ! -s "$PGDATA/PG_VERSION" ]; then
    echo "replica: waiting for primary ${PRIMARY_HOST} ..."
    until pg_isready -h "$PRIMARY_HOST" -p 5432 -U "$REPLICATION_USER" >/dev/null 2>&1; do sleep 1; done
    echo "replica: cloning primary"
    PGPASSWORD="$REPLICATION_PASSWORD" pg_basebackup \
        -h "$PRIMARY_HOST" -p 5432 -U "$REPLICATION_USER" \
        -D "$PGDATA" -Fp -Xs -P -R -S "${REPLICATION_SLOT:-replica_1}"
    chmod 0700 "$PGDATA"
fi

exec postgres -c hot_standby=on
