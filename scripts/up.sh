#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_ENV_FILE="${ROOT_DIR}/.build/install.env"

# shellcheck disable=SC1091
source "${ROOT_DIR}/scripts/compose-mode.sh"
issabel_compose_init "${ROOT_DIR}" "$@"
issabel_require_no_script_args

python3 "${ROOT_DIR}/scripts/resolve-install-profile.py"
# shellcheck disable=SC1090
source "${BUILD_ENV_FILE}"
issabel_print_compose_mode
"${COMPOSE_CMD[@]}" up -d --build
