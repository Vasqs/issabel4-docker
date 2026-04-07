#!/bin/bash
set -euo pipefail

target_file="/var/www/html/modules/agent_console/index.php"
backup_file="${MODULE_RUNTIME_ROOT}/index.php.orig"
patcher_file="${MODULE_RUNTIME_ROOT}/apply_agent_console_patch.php"

if [ ! -f "$target_file" ]; then
  echo "target file not found: $target_file" >&2
  exit 1
fi

mkdir -p "$MODULE_RUNTIME_ROOT"

if [ ! -f "$backup_file" ]; then
  cp "$target_file" "$backup_file"
fi

cat >"$patcher_file" <<'PHP'
<?php
$targetFile = '/var/www/html/modules/agent_console/index.php';
$contents = file_get_contents($targetFile);

if ($contents === false) {
    fwrite(STDERR, "failed to read target file\n");
    exit(1);
}

// Normalize agent default selection blocks with regex to survive formatting changes.
$patternAgentByUser = "~if\\s*\\(isset\\(\\\$listaAgentes\\['Agent/'\\.\\\$_SESSION\\['issabel_user'\\]\\]\\)\\)\\s*\\n\\s*\\\$smarty->assign\\('ID_AGENT',\\s*'Agent/'\\.\\\$_SESSION\\['issabel_user'\\]\\);~m";
$replacementAgentGeneric = <<<'TXT'
        foreach (array_keys($listaAgentes) as $k) {
            if (strpos($k, 'Agent/') === 0) {
                $smarty->assign('ID_AGENT', $k);
                break;
            }
        }
TXT;
$contents = preg_replace($patternAgentByUser, $replacementAgentGeneric, $contents);

$patternCallbackFallback = "~if\\s*\\((?:!isset\\(\\\$listaAgentes\\['Agent/'\\.\\\$_SESSION\\['issabel_user'\\]\\]\\)\\s*&&\\s*)?count\\(\\\$listaExtensionesCallback\\)\\s*>\\s*0\\)\\s*\\n\\s*\\\$smarty->assign\\('ID_AGENT',\\s*key\\(\\\$listaExtensionesCallback\\)\\);~m";
$replacementCallbackFallback = <<<'TXT'
        if ($smarty->get_template_vars('ID_AGENT') == '' &&
            count($listaExtensionesCallback) > 0)
            $smarty->assign('ID_AGENT', key($listaExtensionesCallback));
TXT;
$contents = preg_replace($patternCallbackFallback, $replacementCallbackFallback, $contents);

$patternSipFallback = "~if\\s*\\((?:!isset\\(\\\$listaAgentes\\['Agent/'\\.\\\$_SESSION\\['issabel_user'\\]\\]\\)\\s*&&\\s*)?isset\\(\\\$listaAgentes\\['SIP/'\\.\\\$sExtension\\]\\)\\)\\s*\\n\\s*\\\$smarty->assign\\('ID_AGENT',\\s*'SIP/'\\.\\\$sExtension\\);~m";
$replacementSipFallback = <<<'TXT'
                if ($smarty->get_template_vars('ID_AGENT') == '' &&
                    isset($listaAgentes['SIP/'.$sExtension]))
                    $smarty->assign('ID_AGENT', 'SIP/'.$sExtension);
TXT;
$contents = preg_replace($patternSipFallback, $replacementSipFallback, $contents);

// Upgrade path from earlier patch versions that forced SIP/default callback.
$legacyAgentPriorityByUser = <<<'TXT'
        if (isset($listaAgentes['Agent/'.$_SESSION['issabel_user']]))
            $smarty->assign('ID_AGENT', 'Agent/'.$_SESSION['issabel_user']);
TXT;
$newAgentPriorityGeneric = <<<'TXT'
        foreach (array_keys($listaAgentes) as $k) {
            if (strpos($k, 'Agent/') === 0) {
                $smarty->assign('ID_AGENT', $k);
                break;
            }
        }
TXT;
if (strpos($contents, $legacyAgentPriorityByUser) !== false) {
    $contents = str_replace($legacyAgentPriorityByUser, $newAgentPriorityGeneric, $contents, $legacyPriorityCount);
    if ($legacyPriorityCount < 1) {
        fwrite(STDERR, "failed to upgrade agent priority selection\n");
        exit(1);
    }
}

$legacyCallbackFallback = <<<'TXT'
        if (!isset($listaAgentes['Agent/'.$_SESSION['issabel_user']]) &&
            count($listaExtensionesCallback) > 0)
            $smarty->assign('ID_AGENT', key($listaExtensionesCallback));
TXT;
$newCallbackFallback = <<<'TXT'
        if ($smarty->get_template_vars('ID_AGENT') == '' &&
            count($listaExtensionesCallback) > 0)
            $smarty->assign('ID_AGENT', key($listaExtensionesCallback));
TXT;
if (strpos($contents, $legacyCallbackFallback) !== false) {
    $contents = str_replace($legacyCallbackFallback, $newCallbackFallback, $contents, $legacyCallbackFallbackCount);
    if ($legacyCallbackFallbackCount < 1) {
        fwrite(STDERR, "failed to upgrade callback fallback selection\n");
        exit(1);
    }
}

$legacySipDefault = <<<'TXT'
                if (!isset($listaAgentes['Agent/'.$_SESSION['issabel_user']]) &&
                    isset($listaAgentes['SIP/'.$sExtension]))
                    $smarty->assign('ID_AGENT', 'SIP/'.$sExtension);
TXT;
$newSipDefault = <<<'TXT'
                if ($smarty->get_template_vars('ID_AGENT') == '' &&
                    isset($listaAgentes['SIP/'.$sExtension]))
                    $smarty->assign('ID_AGENT', 'SIP/'.$sExtension);
TXT;
if (strpos($contents, $legacySipDefault) !== false) {
    $contents = str_replace($legacySipDefault, $newSipDefault, $contents, $legacySipDefaultCount);
    if ($legacySipDefaultCount < 1) {
        fwrite(STDERR, "failed to upgrade SIP fallback selection\n");
        exit(1);
    }
}

$old = <<<'TXT'
    $listaAgentes = $oPaloConsola->listarAgentes('static');
TXT;
$new = <<<'TXT'
    $listaAgentes = $oPaloConsola->listarAgentes();
TXT;
if (strpos($contents, $old) !== false) {
    $contents = str_replace($old, $new, $contents, $countAllAgents);
    if ($countAllAgents !== 1) {
        fwrite(STDERR, "failed to patch agent list source\n");
        exit(1);
    }
}

if (strpos($contents, "if (\$smarty->get_template_vars('ID_AGENT') == '' &&\n                    isset(\$listaAgentes['SIP/'.\$sExtension]))") === false) {
    $before = <<<'TXT'
                if (isset($listaExtensiones[$sExtension]))
                    $smarty->assign('ID_EXTENSION', $sExtension);

                foreach (array_keys($listaExtensionesCallback) as $k) {
TXT;
    $after = <<<'TXT'
                if (isset($listaExtensiones[$sExtension]))
                    $smarty->assign('ID_EXTENSION', $sExtension);
                if ($smarty->get_template_vars('ID_AGENT') == '' &&
                    isset($listaAgentes['SIP/'.$sExtension]))
                    $smarty->assign('ID_AGENT', 'SIP/'.$sExtension);

                foreach (array_keys($listaExtensionesCallback) as $k) {
TXT;
    $contents = str_replace($before, $after, $contents, $countSipDefault);
    if ($countSipDefault !== 1) {
        fwrite(STDERR, "failed to patch SIP default agent selection\n");
        exit(1);
    }
}

if (strpos($contents, "if (\$smarty->get_template_vars('ID_AGENT') == '' &&\n            count(\$listaExtensionesCallback) > 0)\n            \$smarty->assign('ID_AGENT', key(\$listaExtensionesCallback));") === false) {
    $before = <<<'TXT'
        if (isset($listaAgentes['Agent/'.$_SESSION['issabel_user']]))
            $smarty->assign('ID_AGENT', 'Agent/'.$_SESSION['issabel_user']);
TXT;
    $after = <<<'TXT'
        foreach (array_keys($listaAgentes) as $k) {
            if (strpos($k, 'Agent/') === 0) {
                $smarty->assign('ID_AGENT', $k);
                break;
            }
        }
        if ($smarty->get_template_vars('ID_AGENT') == '' &&
            count($listaExtensionesCallback) > 0)
            $smarty->assign('ID_AGENT', key($listaExtensionesCallback));
TXT;
    $contents = str_replace($before, $after, $contents, $countDynamicFallback);
    if ($countDynamicFallback !== 1) {
        fwrite(STDERR, "failed to patch dynamic agent default fallback\n");
        exit(1);
    }
}

if (file_put_contents($targetFile, $contents) === false) {
    fwrite(STDERR, "failed to write target file\n");
    exit(1);
}
PHP

php "$patcher_file"

grep -Fq "\$listaAgentes = \$oPaloConsola->listarAgentes();" "$target_file"
grep -Fq "foreach (array_keys(\$listaAgentes) as \$k)" "$target_file"
grep -Fq "if (\$smarty->get_template_vars('ID_AGENT') == '' &&" "$target_file"
grep -Fq "isset(\$listaAgentes['SIP/'.\$sExtension]))" "$target_file"

if [ -f /etc/issabel.conf ]; then
  mysql_root_password="$(awk -F= '/mysqlrootpwd/ {print $2}' /etc/issabel.conf)"
  if [ -n "${mysql_root_password:-}" ]; then
    mysql -uroot "-p${mysql_root_password}" asterisk <<'SQL'
INSERT INTO queues_details (id, keyword, data, flags)
VALUES
  ('500', 'eventmemberstatus', 'yes', 0),
  ('500', 'eventwhencalled', 'yes', 0)
ON DUPLICATE KEY UPDATE data = VALUES(data);
SQL
  fi
fi

asterisk -rx "database del QPENALTY 500/agents/SIP1001" >/dev/null 2>&1 || true
asterisk -rx "database del QPENALTY 500/agents/S1001" >/dev/null 2>&1 || true
asterisk -rx "database put QPENALTY 500/agents/S1001 0" >/dev/null

# Preserva fluxo legado Agent/N: se a fila de uma campanha ativa não tiver
# nenhum membro Agent/*, injeta os agentes estáticos ativos do Call Center.
if [ -f /etc/issabel.conf ]; then
  mysql_root_password="$(awk -F= '/mysqlrootpwd/ {print $2}' /etc/issabel.conf)"
  if [ -n "${mysql_root_password:-}" ]; then
    active_queues="$(mysql -N -uroot "-p${mysql_root_password}" call_center -e "SELECT DISTINCT queue FROM campaign WHERE estatus='A' AND queue IS NOT NULL AND queue<>'';")"
    legacy_agents="$(mysql -N -uroot "-p${mysql_root_password}" call_center -e "SELECT DISTINCT number FROM agent WHERE estatus='A' AND type='Agent' ORDER BY number;")"

    if [ -n "${active_queues:-}" ] && [ -n "${legacy_agents:-}" ]; then
      while IFS= read -r queue_id; do
        [ -z "${queue_id}" ] && continue
        has_agent_members="$(mysql -N -uroot "-p${mysql_root_password}" asterisk -e "SELECT COUNT(*) FROM queues_details WHERE id='${queue_id}' AND keyword='member' AND data LIKE 'Agent/%';")"
        if [ "${has_agent_members:-0}" = "0" ]; then
          next_flag="$(mysql -N -uroot "-p${mysql_root_password}" asterisk -e "SELECT COALESCE(MAX(flags),-1)+1 FROM queues_details WHERE id='${queue_id}' AND keyword='member';")"
          while IFS= read -r agent_number; do
            [ -z "${agent_number}" ] && continue
            mysql -uroot "-p${mysql_root_password}" asterisk -e "INSERT IGNORE INTO queues_details (id, keyword, data, flags) VALUES ('${queue_id}', 'member', 'Agent/${agent_number},0', ${next_flag});"
            next_flag=$((next_flag + 1))
          done <<< "${legacy_agents}"
        fi
      done <<< "${active_queues}"
    fi
  fi
fi

asterisk -rx "queue reload all" >/dev/null
/etc/rc.d/init.d/issabeldialer restart >/dev/null 2>&1 || true
