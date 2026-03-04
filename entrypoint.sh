#!/bin/sh
mkdir -p /app/data/conditions /app/data/symptoms /app/data/medicines /app/data/treatments
exec "$@"
