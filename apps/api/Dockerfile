# ==========================================
# Stage 1: Build & Dependencies (Builder)
# ==========================================
FROM node:22-slim AS builder

WORKDIR /app

# Install OpenSSL required by Prisma CLI and engine
RUN apt-get update && apt-get install -y --no-install-recommends openssl && rm -rf /var/lib/apt/lists/*

# Copy package manifests and install dependencies
COPY package.json package-lock.json* ./
RUN npm ci

# Copy Prisma schema and source files
COPY prisma ./prisma/
COPY src ./src/
COPY tsconfig.json* ./

# Generate Prisma Client during the build step
RUN npx prisma generate

# ==========================================
# Stage 2: Production Runner
# ==========================================
FROM node:22-slim AS runner

WORKDIR /app

# Install curl for container health checks and OpenSSL for Prisma engine
RUN apt-get update && apt-get install -y --no-install-recommends curl openssl && rm -rf /var/lib/apt/lists/*

# Copy package manifests and install dependencies strictly
COPY package.json package-lock.json* ./
RUN npm ci

# Copy application files and generated Prisma client from builder
COPY --from=builder /app/prisma ./prisma
COPY --from=builder /app/src ./src
COPY --from=builder /app/tsconfig.json* ./
COPY --from=builder /app/node_modules/.prisma ./node_modules/.prisma

# Set production environment
ENV NODE_ENV=production
ENV PORT=3000

# Fix permissions
RUN chown -R node:node /app

# Run the application as the unprivileged non-root node user
USER node

EXPOSE 3000

# Launch Cloud API
CMD ["npx", "tsx", "src/server.ts"]
