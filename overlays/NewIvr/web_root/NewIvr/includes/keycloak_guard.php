<?php
if (defined('NEWIVR_KEYCLOAK_GUARD_LOADED')) {
    return;
}
define('NEWIVR_KEYCLOAK_GUARD_LOADED', true);

function newivr_env($name, $default = '') {
    $value = getenv($name);
    if ($value === false || $value === '') {
        static $file_env = null;
        if ($file_env === null) {
            $file_env = array();
            $env_file = '/etc/newivr/keycloak.env';
            if (is_readable($env_file)) {
                $lines = file($env_file, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
                foreach ($lines as $line) {
                    $line = trim($line);
                    if ($line === '' || strpos($line, '#') === 0 || strpos($line, '=') === false) {
                        continue;
                    }
                    list($key, $file_value) = explode('=', $line, 2);
                    $file_env[trim($key)] = trim($file_value, " \t\n\r\0\x0B\"'");
                }
            }
        }
        if (isset($file_env[$name]) && $file_env[$name] !== '') {
            return $file_env[$name];
        }
        return $default;
    }
    return $value;
}

function newivr_parse_env_file($path) {
    $values = array();
    if (!is_readable($path)) {
        return $values;
    }

    $lines = file($path, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
    foreach ($lines as $line) {
        $line = trim($line);
        if ($line === '' || strpos($line, '#') === 0 || strpos($line, '=') === false) {
            continue;
        }
        list($key, $file_value) = explode('=', $line, 2);
        $values[trim($key)] = trim($file_value, " \t\n\r\0\x0B\"'");
    }

    return $values;
}

function newivr_issabel_config() {
    static $config = null;
    if ($config !== null) {
        return $config;
    }

    $config = array();
    $paths = array('/etc/issabel.conf', dirname(dirname(dirname(__DIR__))) . '/.env');
    foreach ($paths as $path) {
        $config = array_merge($config, newivr_parse_env_file($path));
    }

    return $config;
}

function newivr_issabel_value($keys, $default = '') {
    $config = newivr_issabel_config();
    foreach ((array)$keys as $key) {
        if (isset($config[$key]) && $config[$key] !== '') {
            return $config[$key];
        }
    }
    return $default;
}

function newivr_session_start() {
    if (session_id() === '') {
        session_start();
    }
}

function newivr_csrf_token() {
    newivr_session_start();
    if (empty($_SESSION['newivr_csrf_token'])) {
        $_SESSION['newivr_csrf_token'] = newivr_random_token();
    }
    return $_SESSION['newivr_csrf_token'];
}

function newivr_verify_csrf_token($token) {
    newivr_session_start();
    if (!isset($_SESSION['newivr_csrf_token']) || !is_string($token) || $token === '') {
        return false;
    }
    if (function_exists('hash_equals')) {
        return hash_equals($_SESSION['newivr_csrf_token'], $token);
    }
    return $_SESSION['newivr_csrf_token'] === $token;
}

function newivr_is_ajax_request() {
    if (isset($_SERVER['HTTP_ACCEPT']) && strpos($_SERVER['HTTP_ACCEPT'], 'application/json') !== false) {
        return true;
    }
    if (isset($_SERVER['HTTP_X_REQUESTED_WITH']) && strtolower($_SERVER['HTTP_X_REQUESTED_WITH']) === 'xmlhttprequest') {
        return true;
    }
    $uri = isset($_SERVER['REQUEST_URI']) ? $_SERVER['REQUEST_URI'] : '';
    return (bool)preg_match('/\\/(api|dasch|report)\\//', $uri);
}

function newivr_json_response($status, $payload) {
    if (!headers_sent()) {
        http_response_code($status);
        header('Content-Type: application/json; charset=utf-8');
    }
    echo json_encode($payload);
    exit;
}

function newivr_redirect($url) {
    if (!headers_sent()) {
        header('Location: ' . $url);
    }
    exit;
}

function newivr_current_page() {
    return basename(isset($_SERVER['SCRIPT_NAME']) ? $_SERVER['SCRIPT_NAME'] : '');
}

function newivr_public_pages() {
    return array(
        'login.php',
        'keycloak_login.php',
        'keycloak_callback.php',
        'logout.php'
    );
}

function newivr_is_public_page() {
    return in_array(newivr_current_page(), newivr_public_pages(), true);
}

function newivr_base_url() {
    $https = isset($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== '' && $_SERVER['HTTPS'] !== 'off';
    $scheme = $https ? 'https' : 'http';
    $host = isset($_SERVER['HTTP_HOST']) ? $_SERVER['HTTP_HOST'] : 'localhost';
    return $scheme . '://' . $host . '/NewIvr';
}

function newivr_keycloak_config() {
    $issuer = rtrim(newivr_env('NEWIVR_KEYCLOAK_ISSUER'), '/');
    if ($issuer === '') {
        $http_host = newivr_env('NEWIVR_KEYCLOAK_HTTP_HOST', '127.0.0.1');
        $http_port = newivr_env('NEWIVR_KEYCLOAK_HTTP_PORT', '18080');
        if ($http_host !== '' && $http_port !== '') {
            $issuer = 'http://' . $http_host . ':' . $http_port . '/realms/newivr';
        }
    }
    return array(
        'issuer' => $issuer,
        'client_id' => newivr_env('NEWIVR_KEYCLOAK_CLIENT_ID', 'newivr'),
        'client_secret' => newivr_env('NEWIVR_KEYCLOAK_CLIENT_SECRET', 'newivr-hml-secret'),
        'scopes' => newivr_env('NEWIVR_KEYCLOAK_SCOPES', 'openid profile email'),
        'admin_role' => newivr_env('NEWIVR_KEYCLOAK_ADMIN_ROLE', 'newivr-admin'),
        'agent_role' => newivr_env('NEWIVR_KEYCLOAK_AGENT_ROLE', 'newivr-agente'),
        'session_timeout' => (int)newivr_env('NEWIVR_SESSION_TIMEOUT', '3600'),
        'redirect_uri' => newivr_env('NEWIVR_KEYCLOAK_REDIRECT_URI', newivr_base_url() . '/keycloak_callback.php')
    );
}

function newivr_db_config() {
    $host = newivr_env('NEWIVR_DB_HOST');
    if ($host === '') {
        $host = newivr_issabel_value(array('NEWIVR_DB_HOST', 'ISSABEL_CALLCENTER_DB_HOST', 'MYSQLHOST', 'mysqlhost'), 'localhost');
    }

    $name = newivr_env('NEWIVR_DB_NAME');
    if ($name === '') {
        $name = newivr_issabel_value(array('NEWIVR_DB_NAME', 'ISSABEL_CALLCENTER_DB_NAME', 'ISSABEL_CALLCENTER_DB_DATABASE', 'MYSQLDATABASE', 'mysqldbname'), 'call_center');
    }

    $user = newivr_env('NEWIVR_DB_USER');
    if ($user === '') {
        $user = newivr_issabel_value(array('NEWIVR_DB_USER', 'ISSABEL_CALLCENTER_DB_USER', 'MYSQLUSER', 'mysqluser'), 'asterisk');
    }

    $pass = newivr_env('NEWIVR_DB_PASS');
    if ($pass === '') {
        $pass = newivr_issabel_value(array('NEWIVR_DB_PASS', 'ISSABEL_CALLCENTER_DB_PASSWORD', 'MYSQLPASSWORD', 'mysqlpwd'), 'asterisk');
    }

    return array(
        'host' => $host,
        'name' => $name,
        'user' => $user,
        'pass' => $pass
    );
}

function newivr_pbx_db_config() {
    return array(
        'host' => newivr_issabel_value(array('ISSABEL_PBX_DB_HOST', 'AMPDBHOST', 'MYSQLHOST', 'mysqlhost'), 'localhost'),
        'name' => newivr_issabel_value(array('ISSABEL_PBX_DB_NAME', 'ISSABEL_PBX_DB_DATABASE', 'AMPDBNAME'), 'asteriskcdrdb'),
        'user' => newivr_issabel_value(array('ISSABEL_PBX_DB_USER', 'AMPDBUSER'), 'asteriskuser'),
        'pass' => newivr_issabel_value(array('ISSABEL_PBX_DB_PASSWORD', 'AMPDBPASS'), 'amp109')
    );
}

function newivr_asterisk_db_config() {
    return array(
        'host' => newivr_issabel_value(array('ISSABEL_ASTERISK_DB_HOST', 'ISSABEL_PBX_DB_HOST', 'AMPDBHOST', 'MYSQLHOST', 'mysqlhost'), 'localhost'),
        'name' => newivr_issabel_value(array('ISSABEL_ASTERISK_DB_NAME', 'ISSABEL_PBX_DIALPLAN_DB_NAME'), 'asterisk'),
        'user' => newivr_issabel_value(array('ISSABEL_ASTERISK_DB_USER', 'ISSABEL_PBX_DB_USER', 'AMPDBUSER'), 'asteriskuser'),
        'pass' => newivr_issabel_value(array('ISSABEL_ASTERISK_DB_PASSWORD', 'ISSABEL_PBX_DB_PASSWORD', 'AMPDBPASS'), 'amp109')
    );
}

function newivr_webphone_config() {
    $base_url = newivr_env('NEWIVR_WEBPHONE_BASE_URL');
    if ($base_url === '') {
        $public_base = newivr_issabel_value(array('NEWIVR_PUBLIC_BASE_URL'), '');
        if ($public_base === '') {
            $redirect_uri = newivr_env('NEWIVR_KEYCLOAK_REDIRECT_URI');
            if ($redirect_uri !== '' && substr($redirect_uri, -22) === '/keycloak_callback.php') {
                $public_base = substr($redirect_uri, 0, -22);
            }
        }
        if ($public_base === '') {
            $public_base = newivr_base_url();
        }
        $base_url = rtrim($public_base, '/') . '/webphonemonitor/index.php';
    }

    $server = newivr_env('NEWIVR_WEBPHONE_SERVER');
    if ($server === '') {
        $server = parse_url($base_url, PHP_URL_HOST);
    }

    return array(
        'base_url' => $base_url,
        'server' => $server !== null ? $server : '',
        'secret' => newivr_env('NEWIVR_WEBPHONE_SECRET'),
        'port' => newivr_env('NEWIVR_WEBPHONE_PORT', '8089'),
        'user' => newivr_env('NEWIVR_WEBPHONE_USER', 'agente')
    );
}

function newivr_random_token() {
    if (function_exists('openssl_random_pseudo_bytes')) {
        $strong = false;
        $bytes = openssl_random_pseudo_bytes(32, $strong);
        if ($bytes !== false) {
            return rtrim(strtr(base64_encode($bytes), '+/', '-_'), '=');
        }
    }
    return sha1(uniqid('', true) . mt_rand());
}

function newivr_http_request($url, $method = 'GET', $body = null, $headers = array()) {
    if (function_exists('curl_init')) {
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 15);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, true);
        curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, 2);
        if ($method === 'POST') {
            curl_setopt($ch, CURLOPT_POST, true);
            curl_setopt($ch, CURLOPT_POSTFIELDS, $body);
        }
        if (!empty($headers)) {
            curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
        }
        $response = curl_exec($ch);
        $status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $error = curl_error($ch);
        curl_close($ch);
        if ($response === false || $status >= 400) {
            throw new Exception('Keycloak HTTP request failed: ' . $error . ' status=' . $status);
        }
        return $response;
    }

    $opts = array('http' => array('method' => $method, 'timeout' => 15, 'header' => implode("\r\n", $headers)));
    if ($body !== null) {
        $opts['http']['content'] = $body;
    }
    $response = file_get_contents($url, false, stream_context_create($opts));
    if ($response === false) {
        throw new Exception('Keycloak HTTP request failed');
    }
    return $response;
}

function newivr_json_get($url) {
    $payload = json_decode(newivr_http_request($url), true);
    if (!is_array($payload)) {
        throw new Exception('Invalid JSON from Keycloak');
    }
    return $payload;
}

function newivr_discovery() {
    $config = newivr_keycloak_config();
    if ($config['issuer'] === '') {
        throw new Exception('NEWIVR_KEYCLOAK_ISSUER is not configured');
    }
    return newivr_json_get($config['issuer'] . '/.well-known/openid-configuration');
}

function newivr_base64url_decode($value) {
    $value = strtr($value, '-_', '+/');
    $pad = strlen($value) % 4;
    if ($pad) {
        $value .= str_repeat('=', 4 - $pad);
    }
    return base64_decode($value);
}

function newivr_jwt_parts($jwt) {
    $parts = explode('.', $jwt);
    if (count($parts) !== 3) {
        throw new Exception('Invalid JWT format');
    }
    $header = json_decode(newivr_base64url_decode($parts[0]), true);
    $payload = json_decode(newivr_base64url_decode($parts[1]), true);
    if (!is_array($header) || !is_array($payload)) {
        throw new Exception('Invalid JWT JSON');
    }
    return array($header, $payload, $parts[0] . '.' . $parts[1], newivr_base64url_decode($parts[2]));
}

function newivr_asn1_length($length) {
    if ($length < 128) {
        return chr($length);
    }
    $out = '';
    while ($length > 0) {
        $out = chr($length & 0xff) . $out;
        $length >>= 8;
    }
    return chr(0x80 | strlen($out)) . $out;
}

function newivr_asn1_integer($bytes) {
    $bytes = ltrim($bytes, "\x00");
    if ($bytes === '') {
        $bytes = "\x00";
    }
    if (ord($bytes[0]) > 0x7f) {
        $bytes = "\x00" . $bytes;
    }
    return "\x02" . newivr_asn1_length(strlen($bytes)) . $bytes;
}

function newivr_asn1_sequence($bytes) {
    return "\x30" . newivr_asn1_length(strlen($bytes)) . $bytes;
}

function newivr_asn1_bit_string($bytes) {
    $bytes = "\x00" . $bytes;
    return "\x03" . newivr_asn1_length(strlen($bytes)) . $bytes;
}

function newivr_jwk_to_pem($jwk) {
    if (!isset($jwk['n']) || !isset($jwk['e'])) {
        throw new Exception('Invalid RSA JWK');
    }
    $modulus = newivr_base64url_decode($jwk['n']);
    $exponent = newivr_base64url_decode($jwk['e']);
    $rsa_public_key = newivr_asn1_sequence(newivr_asn1_integer($modulus) . newivr_asn1_integer($exponent));
    $algorithm = "\x30\x0d\x06\x09\x2a\x86\x48\x86\xf7\x0d\x01\x01\x01\x05\x00";
    $spki = newivr_asn1_sequence($algorithm . newivr_asn1_bit_string($rsa_public_key));
    return "-----BEGIN PUBLIC KEY-----\n" . chunk_split(base64_encode($spki), 64, "\n") . "-----END PUBLIC KEY-----\n";
}

function newivr_find_jwk($jwks, $kid) {
    if (!isset($jwks['keys']) || !is_array($jwks['keys'])) {
        throw new Exception('Invalid JWKS');
    }
    foreach ($jwks['keys'] as $key) {
        if (isset($key['kid']) && $key['kid'] === $kid) {
            return $key;
        }
    }
    throw new Exception('JWT signing key not found');
}

function newivr_token_audience_matches($claims, $client_id) {
    if (isset($claims['aud'])) {
        if (is_array($claims['aud']) && in_array($client_id, $claims['aud'], true)) {
            return true;
        }
        if (is_string($claims['aud']) && $claims['aud'] === $client_id) {
            return true;
        }
    }
    return isset($claims['azp']) && $claims['azp'] === $client_id;
}

function newivr_verify_jwt($jwt, $jwks_uri) {
    $config = newivr_keycloak_config();
    list($header, $claims, $signed, $signature) = newivr_jwt_parts($jwt);
    if (!isset($header['alg']) || $header['alg'] !== 'RS256') {
        throw new Exception('Unsupported JWT algorithm');
    }
    $jwks = newivr_json_get($jwks_uri);
    $jwk = newivr_find_jwk($jwks, isset($header['kid']) ? $header['kid'] : '');
    $verified = openssl_verify($signed, $signature, newivr_jwk_to_pem($jwk), OPENSSL_ALGO_SHA256);
    if ($verified !== 1) {
        throw new Exception('Invalid JWT signature');
    }
    if (!isset($claims['iss']) || rtrim($claims['iss'], '/') !== $config['issuer']) {
        throw new Exception('Invalid JWT issuer');
    }
    if (!newivr_token_audience_matches($claims, $config['client_id'])) {
        throw new Exception('Invalid JWT audience');
    }
    if (!isset($claims['exp']) || time() >= (int)$claims['exp']) {
        throw new Exception('Expired JWT');
    }
    return $claims;
}

function newivr_extract_roles($claims) {
    $roles = array();
    if (isset($claims['realm_access']['roles']) && is_array($claims['realm_access']['roles'])) {
        $roles = array_merge($roles, $claims['realm_access']['roles']);
    }
    $config = newivr_keycloak_config();
    $client_id = $config['client_id'];
    if (isset($claims['resource_access'][$client_id]['roles']) && is_array($claims['resource_access'][$client_id]['roles'])) {
        $roles = array_merge($roles, $claims['resource_access'][$client_id]['roles']);
    }
    return array_values(array_unique($roles));
}

function newivr_profile_id_from_roles($roles) {
    $config = newivr_keycloak_config();
    if (in_array($config['admin_role'], $roles, true) || in_array('newivr-admin', $roles, true)) {
        return 1;
    }
    if (in_array($config['agent_role'], $roles, true) || in_array('newivr-agente', $roles, true)) {
        return 6;
    }
    return 0;
}

function newivr_db_connect() {
    $db = newivr_db_config();
    $dsn = 'mysql:host=' . $db['host'] . ';dbname=' . $db['name'] . ';charset=utf8';
    $pdo = new PDO($dsn, $db['user'], $db['pass']);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
    $pdo->exec("SET NAMES 'utf8'");
    return $pdo;
}

function newivr_local_user_by_username($username) {
    $pdo = newivr_db_connect();
    $stmt = $pdo->prepare("SELECT * FROM app_ivr_users WHERE username = :username AND status = 'active' LIMIT 1");
    $stmt->bindParam(':username', $username, PDO::PARAM_STR);
    $stmt->execute();
    $user = $stmt->fetch();
    return $user ? $user : false;
}

function newivr_update_local_session_fields($user_id) {
    try {
        $pdo = newivr_db_connect();
        $stmt = $pdo->prepare("UPDATE app_ivr_users SET last_login = NOW(), last_access = NOW(), session_expiry = DATE_ADD(NOW(), INTERVAL 1 HOUR) WHERE id = :id");
        $stmt->bindParam(':id', $user_id, PDO::PARAM_INT);
        $stmt->execute();
    } catch (Exception $e) {
        error_log('NewIvr Keycloak session field update failed: ' . $e->getMessage());
    }
}

function newivr_establish_session($claims, $access_claims, $id_token) {
    $username = isset($claims['preferred_username']) ? $claims['preferred_username'] : '';
    if ($username === '' && isset($access_claims['preferred_username'])) {
        $username = $access_claims['preferred_username'];
    }
    if ($username === '') {
        throw new Exception('preferred_username claim is required');
    }

    $roles = array_merge(newivr_extract_roles($claims), newivr_extract_roles($access_claims));
    $profile_id = newivr_profile_id_from_roles($roles);
    if ($profile_id === 0) {
        throw new Exception('User has no valid NewIvr role');
    }

    $user = newivr_local_user_by_username($username);
    if (!$user) {
        throw new Exception('Keycloak user is not active in app_ivr_users');
    }

    newivr_session_start();
    session_regenerate_id(true);
    $_SESSION['logged_in'] = true;
    $_SESSION['auth_provider'] = 'keycloak';
    $_SESSION['user_id'] = isset($user['id']) ? $user['id'] : 0;
    $_SESSION['username'] = $username;
    $_SESSION['full_name'] = isset($user['full_name']) ? $user['full_name'] : $username;
    $_SESSION['email'] = isset($user['email']) ? $user['email'] : (isset($claims['email']) ? $claims['email'] : '');
    $_SESSION['profile_id'] = $profile_id;
    $_SESSION['extension'] = isset($user['extension']) ? $user['extension'] : '';
    $_SESSION['keycloak_roles'] = $roles;
    $_SESSION['keycloak_id_token'] = $id_token;
    $_SESSION['login_time'] = time();

    newivr_update_local_session_fields((int)$_SESSION['user_id']);
    return $profile_id;
}

function newivr_authenticated() {
    newivr_session_start();
    if (!isset($_SESSION['logged_in']) || $_SESSION['logged_in'] !== true) {
        return false;
    }
    if (!isset($_SESSION['auth_provider']) || $_SESSION['auth_provider'] !== 'keycloak') {
        return false;
    }
    $config = newivr_keycloak_config();
    $timeout = $config['session_timeout'];
    if ($timeout > 0 && isset($_SESSION['login_time']) && (time() - $_SESSION['login_time']) > $timeout) {
        return false;
    }
    return true;
}

function newivr_require_authentication() {
    if (newivr_authenticated()) {
        session_write_close();
        return;
    }
    if (newivr_is_ajax_request()) {
        newivr_json_response(401, array('success' => false, 'error' => 'unauthorized'));
    }
    newivr_redirect('/NewIvr/keycloak_login.php');
}

function newivr_require_admin_session() {
    newivr_require_authentication();
    newivr_session_start();
    if (!isset($_SESSION['profile_id']) || (int)$_SESSION['profile_id'] !== 1) {
        if (newivr_is_ajax_request()) {
            newivr_json_response(403, array('success' => false, 'error' => 'forbidden'));
        }
        http_response_code(403);
        echo 'Acesso negado';
        exit;
    }
    session_write_close();
}

function newivr_require_admin_post_csrf() {
    newivr_require_admin_session();
    $method = isset($_SERVER['REQUEST_METHOD']) ? strtoupper($_SERVER['REQUEST_METHOD']) : '';
    if ($method !== 'POST') {
        newivr_json_response(405, array('success' => false, 'error' => 'method_not_allowed'));
    }
    $token = isset($_POST['csrf_token']) ? $_POST['csrf_token'] : '';
    if (!newivr_verify_csrf_token($token)) {
        newivr_json_response(403, array('success' => false, 'error' => 'invalid_csrf'));
    }
}

if (PHP_SAPI !== 'cli' && !defined('NEWIVR_SKIP_AUTH_BOOTSTRAP') && !newivr_is_public_page()) {
    newivr_require_authentication();
}
?>
