#!/bin/sh
set -e

echo "Running Prisma migrations..."
npx prisma migrate deploy --schema=./apps/api/prisma/schema.prisma

echo "Starting Cloud API server..."
exec npx tsx apps/api/src/server.ts
