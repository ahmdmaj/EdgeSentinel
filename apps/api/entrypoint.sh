#!/bin/sh
set -e

echo "Running Prisma migrations..."
npx prisma migrate deploy

echo "Starting Cloud API server..."
exec npx tsx src/server.ts
