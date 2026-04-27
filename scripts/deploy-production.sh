#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILE_FILE="${ROOT_DIR}/.issabel-install.conf"
BUILD_ENV_FILE="${ROOT_DIR}/.build/install.env"

# shellcheck disable=SC1091
source "${ROOT_DIR}/scripts/compose-mode.sh"

export ISSABEL_COMPOSE_MODE=hostnet
export ISSABEL_HTTPS_PORT="${ISSABEL_HTTPS_PORT:-${ISSABEL_HOSTNET_HTTPS_PORT:-443}}"

require_file() {
  local path="$1"

  if [[ ! -f "$path" ]]; then
    echo "missing required build artifact: $path" >&2
    echo "run ./scripts/up.sh or resolve the install profile before deploying to production" >&2
    exit 1
  fi
}

issabel_compose_init "${ROOT_DIR}"
issabel_require_no_script_args

require_file "${PROFILE_FILE}"
require_file "${BUILD_ENV_FILE}"

# shellcheck disable=SC1090
source "${BUILD_ENV_FILE}"

issabel_print_compose_mode
"${COMPOSE_CMD[@]}" build issabel
"${COMPOSE_CMD[@]}" up -d --force-recreate issabel
"${ROOT_DIR}/scripts/sync-workspace.sh"
"${COMPOSE_CMD[@]}" ps issabel
