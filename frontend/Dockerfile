# frontend/Dockerfile
# ====================
# Multi-stage build: Node builds the Vite app, nginx serves the static dist/.
#
# Build arg:
#   VITE_API_URL  — HTTP base URL of the FastAPI backend.
#                   Default: http://localhost:8000  (local dev fallback)
#                   In docker-compose this is set to http://backend:8000
#                   so the browser can reach the backend via the published port.
#
# Usage (standalone):
#   docker build \
#     --build-arg VITE_API_URL=http://localhost:8000 \
#     -t captionai-frontend \
#     frontend/

# --------------------------------------------------------------------------
# Stage 1 — builder
# --------------------------------------------------------------------------
FROM node:20-alpine AS builder

# Build-time variable — baked into the static bundle by Vite at build time.
# Must be declared BEFORE the RUN npm build step so Vite can read it.
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=${VITE_API_URL}

WORKDIR /app

# Install dependencies first (layer-cached until package*.json changes)
COPY package.json package-lock.json ./
# Install dependencies with BuildKit cache mount.
# /root/.npm is the npm global cache — survives between builds on the host.
RUN --mount=type=cache,target=/root/.npm \
    npm ci --silent

# Copy source and build
COPY . .
RUN npm run build
# Output lands in /app/dist/

# --------------------------------------------------------------------------
# Stage 2 — runtime
# --------------------------------------------------------------------------
FROM nginx:alpine

# Remove the default nginx welcome page
RUN rm -rf /usr/share/nginx/html/*

# Copy the compiled React app from the builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# nginx config: serve index.html for all routes (React Router / SPA support)
RUN printf 'server {\n\
    listen 80;\n\
    root /usr/share/nginx/html;\n\
    index index.html;\n\
    # Serve index.html for any route not matched by a static file\n\
    location / {\n\
        try_files $uri $uri/ /index.html;\n\
    }\n\
}\n' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
