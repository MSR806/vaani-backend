#!/bin/bash
set -e
export PYTHONUNBUFFERED=1

echo "Starting nginx......"
exec service nginx start &

echo "Starting FastAPI application with gunicorn......"
exec gunicorn app.main:app \
    -k uvicorn.workers.UvicornWorker \
    --bind unix:/ecs-vaani.sock \
    -w 4 \
    --timeout 300
