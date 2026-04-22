#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# shellcheck disable=SC1091
source "${ROOT_DIR}/scripts/compose-mode.sh"
issabel_compose_init "${ROOT_DIR}" "$@"
issabel_require_no_script_args
issabel_print_compose_mode
"${COMPOSE_CMD[@]}" down
