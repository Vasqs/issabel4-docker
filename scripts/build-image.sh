#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_ENV_FILE="${ROOT_DIR}/.build/install.env"

python3 "${ROOT_DIR}/scripts/resolve-install-profile.py"
# shellcheck disable=SC1090
source "${BUILD_ENV_FILE}"
docker compose -f "${ROOT_DIR}/docker-compose.yml" build issabel
