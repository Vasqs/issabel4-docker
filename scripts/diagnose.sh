#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "${ROOT_DIR}/scripts/compose-mode.sh"
issabel_compose_init "${ROOT_DIR}" "$@"
issabel_require_no_script_args
issabel_print_compose_mode

"${COMPOSE_CMD[@]}" ps
echo "---"
"${COMPOSE_CMD[@]}" exec -T issabel bash -lc 'ps -ef | egrep "bootstrap-issabel|mysqld|httpd|asterisk" | grep -v grep' || true
echo "---"
"${COMPOSE_CMD[@]}" exec -T issabel bash -lc 'ss -ltnup | egrep ":80 |:443 |:3306 |:5060 " || true' || true
echo "---"
"${COMPOSE_CMD[@]}" exec -T issabel bash -lc '
  SIP_SETTINGS="$(asterisk -rx "sip show settings" 2>/dev/null || true)"
  if [ -n "$SIP_SETTINGS" ]; then
    echo "$SIP_SETTINGS" | egrep -i "UDP Bindaddress|SIP address remapping|Externhost|Externaddr|Localnet" || true
    if echo "$SIP_SETTINGS" | grep -q "Externhost:[[:space:]]*SEU_IP_PUBLICO_OU_DNS"; then
      echo "WARN: sip_general_custom.conf still has placeholder externhost=SEU_IP_PUBLICO_OU_DNS (audio/DTMF will break for NAT clients)" >&2
    fi
    if echo "$SIP_SETTINGS" | grep -q "SIP address remapping:[[:space:]]*Disabled"; then
      echo "WARN: SIP address remapping is disabled (externip/externhost not set or not resolvable)" >&2
    fi
  fi
' || true
echo "---"
"${COMPOSE_CMD[@]}" exec -T issabel bash -lc 'tail -n 80 /var/log/issabel-mysqld-safe.log /var/log/mariadb/mariadb.log /var/log/issabel-httpd.log /var/log/issabel-asterisk.log 2>/dev/null || true' || true
