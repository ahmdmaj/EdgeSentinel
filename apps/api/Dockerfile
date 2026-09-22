# ==========================================
# Stage 1: Build & Dependencies (Builder)
# ==========================================
FROM node:22-slim AS builder

WORKDIR /app

# Install OpenSSL required by Prisma CLI and engine
RUN apt-get update && apt-get install -y --no-install-recommends openssl && rm -rf /var/lib/apt/lists/*

# Copy monorepo root manifests (lockfile lives here in an NPM workspace)
COPY package.json package-lock.json ./

# Copy the API workspace package.json so npm ci resolves its deps
COPY apps/api/package.json ./apps/api/

# Install all workspace dependencies using the root lockfile
RUN npm ci --workspace=apps/api

# Copy Prisma schema and source files
COPY apps/api/prisma ./apps/api/prisma/
COPY apps/api/src ./apps/api/src/
COPY apps/api/tsconfig.json* ./apps/api/

# Generate Prisma Client during the build step
RUN npx prisma generate --schema=./apps/api/prisma/schema.prisma

# ==========================================
# Stage 2: Production Runner
# ==========================================
FROM node:22-slim AS runner

WORKDIR /app

# Install curl for container health checks and OpenSSL for Prisma engine
RUN apt-get update && apt-get install -y --no-install-recommends curl openssl && rm -rf /var/lib/apt/lists/*

# Copy monorepo manifests and install production deps
COPY package.json package-lock.json ./
COPY apps/api/package.json ./apps/api/

RUN npm ci --workspace=apps/api --omit=dev

# Copy application files and generated Prisma client from builder
COPY --from=builder /app/apps/api/prisma ./apps/api/prisma
COPY --from=builder /app/apps/api/src ./apps/api/src
COPY --from=builder /app/apps/api/tsconfig.json* ./apps/api/
COPY --from=builder /app/node_modules/.prisma ./node_modules/.prisma

# Copy entrypoint script
COPY apps/api/entrypoint.sh ./apps/api/entrypoint.sh

# Set production environment
ENV NODE_ENV=production
ENV PORT=3000

# Fix permissions and make entrypoint executable
RUN chown -R node:node /app && chmod +x /app/apps/api/entrypoint.sh

# Run the application as the unprivileged non-root node user
USER node

EXPOSE 3000

# Run migrations then start the API server
CMD ["/bin/sh", "/app/apps/api/entrypoint.sh"]
