#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE=(docker compose -f "${ROOT_DIR}/docker-compose.yml")

"${COMPOSE[@]}" ps
echo "---"
"${COMPOSE[@]}" exec -T issabel bash -lc 'ps -ef | egrep "bootstrap-issabel|mysqld|httpd|asterisk" | grep -v grep' || true
echo "---"
"${COMPOSE[@]}" exec -T issabel bash -lc 'ss -ltnp | egrep ":80 |:443 |:3306 " || true' || true
echo "---"
"${COMPOSE[@]}" exec -T issabel bash -lc 'tail -n 80 /var/log/issabel-mysqld-safe.log /var/log/mariadb/mariadb.log /var/log/issabel-httpd.log /var/log/issabel-asterisk.log 2>/dev/null || true' || true
