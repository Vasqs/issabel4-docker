#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Container-side sync uses rsync, reads from /workspace and publishes modules to /var/www/html/modules.
docker compose -f "${ROOT_DIR}/docker-compose.yml" exec -T issabel /usr/local/bin/sync-workspace "$@"
