#!/bin/sh
# docker-entrypoint.sh
# Writes the nginx config at container start so nginx listens on the
# Railway-injected $PORT (defaults to 80 if not set).
PORT="${PORT:-80}"

cat > /etc/nginx/conf.d/default.conf <<EOF
server {
    listen ${PORT};
    root /usr/share/nginx/html;
    index index.html;

    # Serve index.html for any route not matched by a static file (SPA support)
    location / {
        try_files \$uri \$uri/ /index.html;
    }
}
EOF

exec "$@"
