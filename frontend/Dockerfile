# frontend/Dockerfile
# ====================
# Multi-stage build: Node builds the Vite app, nginx serves the static dist/.
# Railway-compatible: no BuildKit cache mounts.
#
# Build arg (set in Railway Variables dashboard → passed as Build Arg):
#   VITE_API_URL  — Full public URL of the deployed FastAPI backend.
#                   e.g. https://captionai-backend.up.railway.app
#                   This is baked into the JS bundle at build time by Vite.
#                   The browser makes requests directly to this URL, so it
#                   must be the Railway public domain, NOT an internal address.
#
# Usage (standalone):
#   docker build \
#     --build-arg VITE_API_URL=https://your-backend.up.railway.app \
#     -t captionai-frontend \
#     frontend/

# --------------------------------------------------------------------------
# Stage 1 — builder
# --------------------------------------------------------------------------
FROM node:20-alpine AS builder

# Build-time variable — baked into the static bundle by Vite at build time.
# Must be declared BEFORE the RUN npm build step so Vite can read it.
# Railway: set VITE_API_URL in the frontend service Variables dashboard.
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=${VITE_API_URL}

WORKDIR /app

# Install dependencies first (layer-cached until package*.json changes)
COPY package.json package-lock.json ./
RUN npm ci --silent

# Copy source and build
COPY . .
RUN npm run build
# Output lands in /app/dist/

# --------------------------------------------------------------------------
# Stage 2 — runtime (nginx)
# Railway injects $PORT — nginx must listen on it.
# --------------------------------------------------------------------------
FROM nginx:alpine

# Remove the default nginx welcome page
RUN rm -rf /usr/share/nginx/html/*

# Copy the compiled React app from the builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Generate nginx config at container start using the injected $PORT.
# We use an entrypoint script so $PORT is expanded at runtime, not build time.
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 80

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
