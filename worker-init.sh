#!/bin/bash
set -e
export PYTHONUNBUFFERED=1

echo "Starting RQ Worker......"
exec python -m rq.cli worker --url $REDIS_URL default high low
