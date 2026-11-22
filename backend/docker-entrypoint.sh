#!/bin/sh
# Punto de entrada del contenedor del backend.
set -e

# Aplica/actualiza el esquema de forma idempotente. En una base nueva crea las
# tablas desde los modelos; en una existente agrega columnas e índices.
python migrate_mr.py

exec gunicorn \
    --bind 0.0.0.0:5000 \
    --workers "${GUNICORN_WORKERS:-1}" \
    --threads "${GUNICORN_THREADS:-4}" \
    --timeout "${GUNICORN_TIMEOUT:-120}" \
    --access-logfile - \
    --error-logfile - \
    run:app
