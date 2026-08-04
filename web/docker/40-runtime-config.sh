#!/bin/sh
set -eu

cat > /usr/share/nginx/html/runtime-config.js <<CONFIG
window.__WEB_CONFIG__ = {
  APP_NAME: "${WEB_APP_NAME:-HostGator Analytics}",
  APP_ENV: "${WEB_APP_ENV:-development}",
  PUBLIC_URL: "${WEB_PUBLIC_URL:-http://localhost:5173}",
  API_URL: "${WEB_API_URL:-/api}",
  REQUEST_TIMEOUT_MS: ${WEB_REQUEST_TIMEOUT_MS:-15000},
  REGISTRATION_ENABLED: ${WEB_REGISTRATION_ENABLED:-false},
  CSRF_COOKIE_NAME: "${WEB_CSRF_COOKIE_NAME:-csrf_token}",
  CSRF_HEADER_NAME: "${WEB_CSRF_HEADER_NAME:-X-CSRF-Token}"
};
CONFIG
