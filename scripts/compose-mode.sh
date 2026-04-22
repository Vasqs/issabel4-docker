#!/bin/bash
set -euo pipefail

read_env_default() {
  local env_file="$1"
  local key="$2"

  [ -f "$env_file" ] || return 1
  awk -F '=' -v lookup="$key" '
    $1 == lookup {
      value = substr($0, index($0, "=") + 1)
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", value)
      gsub(/^'\''|'\''$/, "", value)
      gsub(/^"|"$/, "", value)
      print value
    }
  ' "$env_file" | tail -n 1
}

issabel_compose_init() {
  local root_dir="$1"
  shift

  local env_file="${root_dir}/.env"
  local compose_mode="${ISSABEL_COMPOSE_MODE:-}"

  COMPOSE_DESCRIPTION=""
  COMPOSE_FILE=""
  COMPOSE_CMD=(docker compose)
  COMPOSE_SCRIPT_ARGS=()

  while (($# > 0)); do
    case "$1" in
      --bridge)
        compose_mode="bridge"
        shift
        ;;
      --host|--hostnet)
        compose_mode="hostnet"
        shift
        ;;
      --compose-mode)
        if (($# < 2)); then
          echo "missing value for --compose-mode" >&2
          return 1
        fi
        compose_mode="$2"
        shift 2
        ;;
      --compose-mode=*)
        compose_mode="${1#*=}"
        shift
        ;;
      --)
        shift
        while (($# > 0)); do
          COMPOSE_SCRIPT_ARGS+=("$1")
          shift
        done
        break
        ;;
      *)
        COMPOSE_SCRIPT_ARGS+=("$1")
        shift
        ;;
    esac
  done

  if [[ -z "${ISSABEL_COMPOSE_MODE:-}" && -z "$compose_mode" ]]; then
    compose_mode="$(read_env_default "$env_file" "ISSABEL_COMPOSE_MODE" || true)"
  fi
  compose_mode="${compose_mode:-bridge}"

  case "$compose_mode" in
    bridge)
      COMPOSE_DESCRIPTION="bridge"
      COMPOSE_FILE="${root_dir}/docker-compose.yml"
      ;;
    host|hostnet)
      COMPOSE_DESCRIPTION="hostnet"
      COMPOSE_FILE="${root_dir}/docker-compose.hostnet.yml"
      ;;
    *)
      echo "unsupported compose mode: ${compose_mode} (expected bridge or hostnet)" >&2
      return 1
      ;;
  esac

  if [[ ! -f "${COMPOSE_FILE}" ]]; then
    echo "compose file not found: ${COMPOSE_FILE}" >&2
    return 1
  fi

  COMPOSE_CMD+=(-f "${COMPOSE_FILE}")
}

issabel_require_no_script_args() {
  if ((${#COMPOSE_SCRIPT_ARGS[@]} > 0)); then
    echo "unexpected arguments: ${COMPOSE_SCRIPT_ARGS[*]}" >&2
    return 1
  fi
}

issabel_print_compose_mode() {
  echo "Using compose mode: ${COMPOSE_DESCRIPTION} (${COMPOSE_FILE})" >&2
  if [[ "${COMPOSE_DESCRIPTION}" == "hostnet" ]]; then
    echo "Host-network mode is intended for real SIP/RTP traffic on the host network; bridge remains the default local-development mode." >&2
  fi
}
