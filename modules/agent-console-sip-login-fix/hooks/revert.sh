#!/bin/bash
set -euo pipefail

target_file="/var/www/html/modules/agent_console/index.php"
backup_file="${MODULE_RUNTIME_ROOT}/index.php.orig"

if [ -f "$backup_file" ]; then
  cp "$backup_file" "$target_file"
fi

asterisk -rx "database del QPENALTY 500/agents/SIP1001" >/dev/null 2>&1 || true
asterisk -rx "database del QPENALTY 500/agents/S1001" >/dev/null 2>&1 || true
/etc/rc.d/init.d/issabeldialer restart >/dev/null 2>&1 || true
