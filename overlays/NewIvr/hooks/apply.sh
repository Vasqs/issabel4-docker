#!/usr/bin/env bash
set -euo pipefail

KEYCLOAK_VERSION="${NEWIVR_KEYCLOAK_VERSION:-24.0.5}"
JRE_VERSION="${NEWIVR_KEYCLOAK_JRE_VERSION:-17.0.11_9}"
JRE_URL="${NEWIVR_KEYCLOAK_JRE_URL:-https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.11%2B9/OpenJDK17U-jre_x64_linux_hotspot_${JRE_VERSION}.tar.gz}"
KEYCLOAK_URL="${NEWIVR_KEYCLOAK_DIST_URL:-https://github.com/keycloak/keycloak/releases/download/${KEYCLOAK_VERSION}/keycloak-${KEYCLOAK_VERSION}.tar.gz}"

BASE_DIR="${NEWIVR_KEYCLOAK_BASE_DIR:-/opt/newivr/keycloak}"
DOWNLOAD_DIR="${BASE_DIR}/downloads"
JRE_DIR="${BASE_DIR}/jre"
KEYCLOAK_DIR="${BASE_DIR}/keycloak-${KEYCLOAK_VERSION}"
RUN_DIR="/var/run/newivr"
LOG_DIR="/var/log/newivr"
ENV_DIR="/etc/newivr"
ENV_FILE="/etc/newivr/keycloak.env"
PID_FILE="${RUN_DIR}/keycloak.pid"
LOG_FILE="${LOG_DIR}/keycloak.log"
REALM_SOURCE="${OVERLAY_ROOT:-/workspace/overlays/NewIvr}/keycloak/newivr-realm.json"
REALM_TARGET="${KEYCLOAK_DIR}/data/import/newivr-realm.json"

KEYCLOAK_HTTP_HOST="${NEWIVR_KEYCLOAK_HTTP_HOST:-127.0.0.1}"
KEYCLOAK_HTTP_PORT="${NEWIVR_KEYCLOAK_HTTP_PORT:-18080}"
KEYCLOAK_ISSUER="${NEWIVR_KEYCLOAK_ISSUER:-http://${KEYCLOAK_HTTP_HOST}:${KEYCLOAK_HTTP_PORT}/realms/newivr}"
KEYCLOAK_REDIRECT_URI="${NEWIVR_KEYCLOAK_REDIRECT_URI:-https://127.0.0.1:8443/NewIvr/keycloak_callback.php}"
KEYCLOAK_POST_LOGOUT_REDIRECT_URIS="${NEWIVR_KEYCLOAK_POST_LOGOUT_REDIRECT_URIS:-https://127.0.0.1:8443/NewIvr/login.php##https://localhost:8443/NewIvr/login.php}"
KEYCLOAK_CLIENT_ID="${NEWIVR_KEYCLOAK_CLIENT_ID:-newivr}"
KEYCLOAK_CLIENT_SECRET="${NEWIVR_KEYCLOAK_CLIENT_SECRET:-newivr-hml-secret}"

workspace_env_value() {
  local name="$1"
  local path="${OVERLAY_ROOT:-/workspace/overlays/NewIvr}/../../.env"

  [ -r "$path" ] || return 1

  awk -F= -v key="$name" '
    $1 == key {
      sub(/^[^=]*=/, "");
      gsub(/^["'\''"]|["'\''"]$/, "");
      print;
      exit;
    }
  ' "$path"
}

resolve_db_value() {
  local current_value="$1"
  local fallback_env_name="$2"
  local default_value="$3"
  local resolved=""

  if [ -n "$current_value" ]; then
    printf '%s\n' "$current_value"
    return 0
  fi

  resolved="$(workspace_env_value "$fallback_env_name" 2>/dev/null || true)"
  if [ -n "$resolved" ]; then
    printf '%s\n' "$resolved"
    return 0
  fi

  printf '%s\n' "$default_value"
}

NEWIVR_DB_HOST_VALUE="$(resolve_db_value "${NEWIVR_DB_HOST:-}" "ISSABEL_CALLCENTER_DB_HOST" "localhost")"
NEWIVR_DB_NAME_VALUE="$(resolve_db_value "${NEWIVR_DB_NAME:-}" "ISSABEL_CALLCENTER_DB_NAME" "call_center")"
NEWIVR_DB_USER_VALUE="$(resolve_db_value "${NEWIVR_DB_USER:-}" "ISSABEL_CALLCENTER_DB_USER" "asterisk")"
NEWIVR_DB_PASS_VALUE="$(resolve_db_value "${NEWIVR_DB_PASS:-}" "ISSABEL_CALLCENTER_DB_PASSWORD" "asterisk")"

validate_db_identifier() {
  local value="$1"
  [[ "$value" =~ ^[A-Za-z0-9_]+$ ]]
}

mkdir -p "$DOWNLOAD_DIR" "$RUN_DIR" "$LOG_DIR" "$ENV_DIR"

download_once() {
  local url="$1"
  local target="$2"

  if [ -s "$target" ]; then
    return 0
  fi

  curl -fL --retry 3 --connect-timeout 20 -o "${target}.tmp" "$url"
  mv "${target}.tmp" "$target"
}

install_jre() {
  if [ -x "${JRE_DIR}/bin/java" ]; then
    return 0
  fi

  local archive="${DOWNLOAD_DIR}/jre-${JRE_VERSION}.tar.gz"
  rm -rf "$JRE_DIR"
  mkdir -p "$JRE_DIR"
  download_once "$JRE_URL" "$archive"
  tar -xzf "$archive" -C "$JRE_DIR" --strip-components=1
}

install_keycloak() {
  if [ -x "${KEYCLOAK_DIR}/bin/kc.sh" ]; then
    return 0
  fi

  local archive="${DOWNLOAD_DIR}/keycloak-${KEYCLOAK_VERSION}.tar.gz"
  download_once "$KEYCLOAK_URL" "$archive"
  tar -xzf "$archive" -C "$BASE_DIR"
}

write_newivr_env() {
  cat >"$ENV_FILE" <<EOF
NEWIVR_KEYCLOAK_ISSUER=${KEYCLOAK_ISSUER}
NEWIVR_KEYCLOAK_CLIENT_ID=${KEYCLOAK_CLIENT_ID}
NEWIVR_KEYCLOAK_CLIENT_SECRET=${KEYCLOAK_CLIENT_SECRET}
NEWIVR_KEYCLOAK_SCOPES=openid profile email
NEWIVR_KEYCLOAK_REDIRECT_URI=${KEYCLOAK_REDIRECT_URI}
NEWIVR_KEYCLOAK_POST_LOGOUT_REDIRECT_URIS=${KEYCLOAK_POST_LOGOUT_REDIRECT_URIS}
NEWIVR_KEYCLOAK_HTTP_HOST=${KEYCLOAK_HTTP_HOST}
NEWIVR_KEYCLOAK_HTTP_PORT=${KEYCLOAK_HTTP_PORT}
NEWIVR_KEYCLOAK_VERSION=${KEYCLOAK_VERSION}
NEWIVR_KEYCLOAK_ADMIN_USER=${NEWIVR_KEYCLOAK_ADMIN_USER:-admin}
NEWIVR_KEYCLOAK_ADMIN_PASSWORD=${NEWIVR_KEYCLOAK_ADMIN_PASSWORD:-DevKeycloak123}
NEWIVR_KEYCLOAK_ADMIN_ROLE=newivr-admin
NEWIVR_KEYCLOAK_AGENT_ROLE=newivr-agente
NEWIVR_SESSION_TIMEOUT=3600
NEWIVR_DB_HOST=${NEWIVR_DB_HOST_VALUE}
NEWIVR_DB_NAME=${NEWIVR_DB_NAME_VALUE}
NEWIVR_DB_USER=${NEWIVR_DB_USER_VALUE}
NEWIVR_DB_PASS=${NEWIVR_DB_PASS_VALUE}
EOF
  chown root:apache "$ENV_FILE"
  chmod 0640 "$ENV_FILE"
}

install_apache_override() {
  cat >/etc/httpd/conf.d/newivr-htaccess.conf <<'EOF'
<Directory "/var/www/html/NewIvr">
    AllowOverride All
</Directory>
EOF
  httpd -t >/dev/null
  /usr/sbin/httpd -k graceful >/dev/null 2>&1 || true
}

ensure_local_users() {
  local mysql_root_password=""
  local db_name="${NEWIVR_DB_NAME_VALUE}"

  validate_db_identifier "$db_name" || return 1

  if [ -f /etc/issabel.conf ]; then
    mysql_root_password="$(awk -F= '$1 == "mysqlrootpwd" {print $2; exit}' /etc/issabel.conf)"
  fi
  [ -n "$mysql_root_password" ] || return 0

  mysql --socket="${MYSQL_SOCKET:-/var/lib/mysql/mysql.sock}" -uroot --password="$mysql_root_password" <<SQL
CREATE DATABASE IF NOT EXISTS \`${db_name}\` DEFAULT CHARACTER SET utf8;
CREATE TABLE IF NOT EXISTS \`${db_name}\`.app_ivr_users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(100) NOT NULL UNIQUE,
  password VARCHAR(255) NULL,
  full_name VARCHAR(255) NULL,
  email VARCHAR(255) NULL,
  profile_id INT NOT NULL DEFAULT 6,
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  extension VARCHAR(32) NULL,
  Empresa VARCHAR(255) NULL,
  session_id VARCHAR(255) NULL,
  last_login DATETIME NULL,
  last_access DATETIME NULL,
  session_expiry DATETIME NULL,
  created_at DATETIME NULL,
  updated_at DATETIME NULL
) DEFAULT CHARSET=utf8;
INSERT INTO \`${db_name}\`.app_ivr_users
  (username,password,full_name,email,profile_id,status,extension,Empresa,created_at,updated_at)
VALUES
  ('admin','keycloak','NewIvr Admin','admin@newivr.local',1,'active','1001','Homologacao',NOW(),NOW()),
  ('agente','keycloak','NewIvr Agente','agente@newivr.local',6,'active','1002','Homologacao',NOW(),NOW())
ON DUPLICATE KEY UPDATE
  status='active',
  updated_at=NOW();
SQL
}

copy_realm() {
  mkdir -p "$(dirname "$REALM_TARGET")"
  cp "$REALM_SOURCE" "$REALM_TARGET"
}

keycloak_is_running() {
  curl -fsS "${KEYCLOAK_ISSUER}/.well-known/openid-configuration" >/dev/null 2>&1
}

start_keycloak() {
  if keycloak_is_running; then
    return 0
  fi

  if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" >/dev/null 2>&1; then
    kill "$(cat "$PID_FILE")" >/dev/null 2>&1 || true
    sleep 2
  fi

  export JAVA_HOME="$JRE_DIR"
  export PATH="${JRE_DIR}/bin:${PATH}"
  export KEYCLOAK_ADMIN="${NEWIVR_KEYCLOAK_ADMIN_USER:-admin}"
  export KEYCLOAK_ADMIN_PASSWORD="${NEWIVR_KEYCLOAK_ADMIN_PASSWORD:-DevKeycloak123}"
  export KC_HTTP_ENABLED=true
  export KC_HOSTNAME_STRICT=false

  nohup "${KEYCLOAK_DIR}/bin/kc.sh" start-dev \
    --import-realm \
    --http-host="$KEYCLOAK_HTTP_HOST" \
    --http-port="$KEYCLOAK_HTTP_PORT" \
    --hostname-strict=false \
    >>"$LOG_FILE" 2>&1 &
  echo $! >"$PID_FILE"

  for _ in $(seq 1 90); do
    if keycloak_is_running; then
      return 0
    fi
    sleep 1
  done

  tail -n 80 "$LOG_FILE" >&2 || true
  return 1
}

configure_keycloak_client() {
  export JAVA_HOME="$JRE_DIR"
  export PATH="${JRE_DIR}/bin:${PATH}"

  "${KEYCLOAK_DIR}/bin/kcadm.sh" config credentials \
    --server "http://${KEYCLOAK_HTTP_HOST}:${KEYCLOAK_HTTP_PORT}" \
    --realm master \
    --user "${NEWIVR_KEYCLOAK_ADMIN_USER:-admin}" \
    --password "${NEWIVR_KEYCLOAK_ADMIN_PASSWORD:-DevKeycloak123}" \
    >/dev/null

  local client_uuid
  client_uuid="$("${KEYCLOAK_DIR}/bin/kcadm.sh" get clients -r newivr -q clientId="$KEYCLOAK_CLIENT_ID" --fields id --format csv | tr -d '\r"' | head -n 1)"
  if [ -z "$client_uuid" ]; then
    echo "NewIvr Keycloak client not found: ${KEYCLOAK_CLIENT_ID}" >&2
    return 1
  fi

  "${KEYCLOAK_DIR}/bin/kcadm.sh" update "clients/${client_uuid}" -r newivr \
    -s "attributes.\"post.logout.redirect.uris\"=${KEYCLOAK_POST_LOGOUT_REDIRECT_URIS}"
}

install_jre
install_keycloak
copy_realm
write_newivr_env
install_apache_override
ensure_local_users
if [ -x /usr/local/bin/newivr-keycloak ]; then
  /usr/local/bin/newivr-keycloak start
else
  start_keycloak
fi
configure_keycloak_client
