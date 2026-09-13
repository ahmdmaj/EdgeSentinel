FROM node:22-slim
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
RUN npx prisma generate
EXPOSE 3000
CMD ["npx", "tsx", "src/server.ts"]
