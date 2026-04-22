#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Container-side sync uses rsync, reads from /workspace and publishes modules to /var/www/html/modules.
# shellcheck disable=SC1091
source "${ROOT_DIR}/scripts/compose-mode.sh"
issabel_compose_init "${ROOT_DIR}" "$@"
issabel_print_compose_mode
"${COMPOSE_CMD[@]}" exec -T issabel /usr/local/bin/sync-workspace "${COMPOSE_SCRIPT_ARGS[@]}"
