#!/bin/bash
set -euo pipefail

target_file="/opt/issabel/dialer/AMIEventProcess.class.php"
backup_file="${MODULE_RUNTIME_ROOT}/AMIEventProcess.class.php.orig"
patcher_file="${MODULE_RUNTIME_ROOT}/apply_ami_event_patch.php"

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
$targetFile = '/opt/issabel/dialer/AMIEventProcess.class.php';
$contents = file_get_contents($targetFile);

if ($contents === false) {
    fwrite(STDERR, "failed to read target file\n");
    exit(1);
}

if (strpos($contents, "private \$_pendiente_nuevaListaAgentes = NULL;") === false) {
    $before = <<<'TXT'
    private $_pendiente_QueueStatus = NULL;

    private $_tmp_actionid_agents = NULL;
TXT;
    $after = <<<'TXT'
    private $_pendiente_QueueStatus = NULL;

    /* Se guarda la última lista de agentes si llega antes de que la sesión
     * AMI esté lista, para reprocesarla al restablecer la conexión. */
    private $_pendiente_nuevaListaAgentes = NULL;

    private $_tmp_actionid_agents = NULL;
TXT;
    $contents = str_replace($before, $after, $contents, $propertyCount);
    if ($propertyCount !== 1) {
        fwrite(STDERR, "failed to patch pending agent list property\n");
        exit(1);
    }
}

if (strpos($contents, "se procesa lista de agentes retrasada") === false) {
    $before = <<<'TXT'
        // Verificar si existen peticiones QueueStatus pendientes
        if (!is_null($this->_ami) && !is_null($this->_pendiente_QueueStatus) && !$this->_finalizandoPrograma) {
            if (is_null($this->_tmp_actionid_queuestatus)) {
                $this->_log->output("INFO: conexión AMI disponible, se ejecuta consulta QueueStatus retrasada...");
                $this->_iniciarQueueStatus($this->_pendiente_QueueStatus);
                $this->_pendiente_QueueStatus = NULL;
            } else {
                $this->_log->output("INFO: conexión AMI disponible, QueueStatus en progreso, se olvida consulta QueueStatus retrasada...");
                $this->_pendiente_QueueStatus = NULL;
            }
        }

        // Verificar si se ha reiniciado Asterisk en medio de procesamiento
TXT;
    $after = <<<'TXT'
        // Verificar si existen peticiones QueueStatus pendientes
        if (!is_null($this->_ami) && !is_null($this->_pendiente_QueueStatus) && !$this->_finalizandoPrograma) {
            if (is_null($this->_tmp_actionid_queuestatus)) {
                $this->_log->output("INFO: conexión AMI disponible, se ejecuta consulta QueueStatus retrasada...");
                $this->_iniciarQueueStatus($this->_pendiente_QueueStatus);
                $this->_pendiente_QueueStatus = NULL;
            } else {
                $this->_log->output("INFO: conexión AMI disponible, QueueStatus en progreso, se olvida consulta QueueStatus retrasada...");
                $this->_pendiente_QueueStatus = NULL;
            }
        }

        // Verificar si existe una lista de agentes pendiente por conexión AMI
        if (!is_null($this->_ami) && !is_null($this->_pendiente_nuevaListaAgentes) && !$this->_finalizandoPrograma) {
            if (is_null($this->_tmp_actionid_queuestatus)) {
                $this->_log->output("INFO: conexión AMI disponible, se procesa lista de agentes retrasada...");
                list($total_agents, $queueflags) = $this->_pendiente_nuevaListaAgentes;
                $this->_pendiente_nuevaListaAgentes = NULL;
                $this->_ami->asyncCommand(
                    array($this, '_cb_Command_DatabaseShow'),
                    array($total_agents, $queueflags),
                    'database show QPENALTY');
            } else {
                $this->_log->output("INFO: conexión AMI disponible, QueueStatus en progreso, se conserva lista de agentes retrasada...");
            }
        }

        // Verificar si se ha reiniciado Asterisk en medio de procesamiento
TXT;
    $contents = str_replace($before, $after, $contents, $queueBlockCount);
    if ($queueBlockCount !== 1) {
        fwrite(STDERR, "failed to patch pending agent list processing block\n");
        exit(1);
    }
}

if (strpos($contents, "se retrasa petición") === false) {
    $before = <<<'TXT'
        if (is_null($this->_ami)) {
            $this->_log->output('WARN: '.__METHOD__.': no se dispone de conexión Asterisk, se ignora petición...');
            return;
        }
TXT;
    $after = <<<'TXT'
        if (is_null($this->_ami)) {
            $this->_log->output('WARN: '.__METHOD__.': no se dispone de conexión Asterisk, se retrasa petición...');
            $this->_pendiente_nuevaListaAgentes = $datos;
            return;
        }
TXT;
    $contents = str_replace($before, $after, $contents, $messageCount);
    if ($messageCount !== 1) {
        fwrite(STDERR, "failed to patch delayed agent list message\n");
        exit(1);
    }
}

if (strpos($contents, "se conserva sesión de ") === false) {
    $before = <<<'TXT'
        if ($params['PeerStatus'] == 'Unregistered') {
            // Alguna extensión se ha desregistrado. Verificar si es un agente logoneado
            $a = $this->_listaAgentes->buscar('extension', $params['Peer']);
            if (!is_null($a)) {
                // La extensión usada para login se ha desregistrado - deslogonear al agente
                $this->_log->output('INFO: '.__METHOD__.' se detecta desregistro de '.
                    $params['Peer'].' - deslogoneando '.$a->channel.'...');
                $a->forzarLogoffAgente($this->_ami, $this->_log);
            }
    	}
TXT;
    $after = <<<'TXT'
        if ($params['PeerStatus'] == 'Unregistered') {
            // Alguna extensión se ha desregistrado. Buscar agentes usando ese peer.
            $agentesPeer = array();
            foreach ($this->_listaAgentes as $cand) {
                if ($cand->extension == $params['Peer'] &&
                    $cand->estado_consola != 'logged-out') {
                    $agentesPeer[] = $cand;
                }
            }

            if (count($agentesPeer) > 0) {
                /* Priorizar deslogueo de agentes dinámicos (SIP/IAX) para no
                 * derribar una sesión legacy Agent/N que comparta peer. */
                $a = NULL;
                foreach ($agentesPeer as $cand) {
                    if ($cand->type != 'Agent') {
                        $a = $cand;
                        break;
                    }
                }
                if (is_null($a)) $a = $agentesPeer[0];

                if ($a->type == 'Agent') {
                    $this->_log->output('INFO: '.__METHOD__.' se detecta desregistro de '.
                        $params['Peer'].' - se conserva sesión de '.$a->channel.
                        ' (Agent/N legado).');
                } else {
                    $this->_log->output('INFO: '.__METHOD__.' se detecta desregistro de '.
                        $params['Peer'].' - deslogoneando '.$a->channel.'...');
                    $a->forzarLogoffAgente($this->_ami, $this->_log);
                }
            }
    	}
TXT;
    $contents = str_replace($before, $after, $contents, $peerStatusCount);
    if ($peerStatusCount !== 1) {
        fwrite(STDERR, "failed to patch PeerStatus logoff handling\n");
        exit(1);
    }
}

if (file_put_contents($targetFile, $contents) === false) {
    fwrite(STDERR, "failed to write target file\n");
    exit(1);
}
PHP

php "$patcher_file"

grep -Fq 'private $_pendiente_nuevaListaAgentes = NULL;' "$target_file"
grep -Fq "se procesa lista de agentes retrasada" "$target_file"
grep -Fq "se retrasa petición" "$target_file"
grep -Fq "se conserva sesión de " "$target_file"
