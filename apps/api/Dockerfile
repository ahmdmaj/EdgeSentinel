FROM node:22-alpine AS builder
WORKDIR /app
RUN corepack enable pnpm
COPY package.json ./
RUN pnpm install
COPY . .

FROM node:22-alpine
WORKDIR /app
RUN corepack enable pnpm
COPY --from=builder /app ./
EXPOSE 3000
CMD ["pnpm", "start"]
