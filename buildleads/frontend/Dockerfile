FROM node:20-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci

# Copy source — Docker invalidates cache when files change
COPY . .

# Build with empty API URL — nginx proxies /api/ to backend
ENV NEXT_PUBLIC_API_URL=""
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
# Server-side rewrites target the api container
ENV BACKEND_URL=http://api:8000

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000
CMD ["node", "server.js"]
