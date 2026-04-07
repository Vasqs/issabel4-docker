#!/bin/bash
set -euo pipefail

target_file="/opt/issabel/dialer/AMIEventProcess.class.php"
backup_file="${MODULE_RUNTIME_ROOT}/AMIEventProcess.class.php.orig"

if [ -f "$backup_file" ]; then
  cp "$backup_file" "$target_file"
fi
