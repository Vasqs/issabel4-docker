<?php
require_once __DIR__ . '/../../includes/keycloak_guard.php';

function newivr_keycloak_realm_name() {
    $config = newivr_keycloak_config();
    $parts = explode('/realms/', $config['issuer'], 2);
    if (count($parts) !== 2 || $parts[1] === '') {
        throw new Exception('Invalid Keycloak issuer for admin API');
    }
    return $parts[1];
}

function newivr_keycloak_base_url() {
    $config = newivr_keycloak_config();
    $parts = explode('/realms/', $config['issuer'], 2);
    if (count($parts) !== 2 || $parts[0] === '') {
        throw new Exception('Invalid Keycloak issuer for admin API');
    }
    return $parts[0];
}

function newivr_keycloak_admin_request($url, $method, $body, $headers) {
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 20);
    curl_setopt($ch, CURLOPT_CUSTOMREQUEST, $method);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, true);
    curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, 2);
    if ($body !== null) {
        curl_setopt($ch, CURLOPT_POSTFIELDS, $body);
    }
    if (!empty($headers)) {
        curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
    }
    curl_setopt($ch, CURLOPT_HEADER, true);
    $raw = curl_exec($ch);
    $status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $header_size = curl_getinfo($ch, CURLINFO_HEADER_SIZE);
    $error = curl_error($ch);
    curl_close($ch);

    $response_body = ($raw === false) ? '' : substr($raw, $header_size);
    if ($raw === false || $status >= 400) {
        error_log('NewIvr Keycloak admin request failed: ' . $method . ' ' . $url . ' ' . $error . ' status=' . $status . ' body=' . $response_body);
        throw new Exception('Falha ao sincronizar usuario no Keycloak (status=' . $status . ')');
    }

    return array(
        'status' => $status,
        'headers' => substr($raw, 0, $header_size),
        'body' => $response_body
    );
}

function newivr_keycloak_admin_token() {
    $base_url = newivr_keycloak_base_url();
    $body = http_build_query(array(
        'grant_type' => 'password',
        'client_id' => 'admin-cli',
        'username' => newivr_env('NEWIVR_KEYCLOAK_ADMIN_USER', 'admin'),
        'password' => newivr_env('NEWIVR_KEYCLOAK_ADMIN_PASSWORD', 'DevKeycloak123')
    ));
    $response = newivr_keycloak_admin_request(
        $base_url . '/realms/master/protocol/openid-connect/token',
        'POST',
        $body,
        array('Content-Type: application/x-www-form-urlencoded')
    );
    $payload = json_decode($response['body'], true);
    if (!is_array($payload) || empty($payload['access_token'])) {
        throw new Exception('Invalid Keycloak admin token response');
    }
    return $payload['access_token'];
}

function newivr_keycloak_admin_api($method, $path, $payload) {
    $base_url = newivr_keycloak_base_url();
    $realm = newivr_keycloak_realm_name();
    $token = newivr_keycloak_admin_token();
    $body = $payload === null ? null : json_encode($payload);
    $headers = array('Authorization: Bearer ' . $token);
    if ($body !== null) {
        $headers[] = 'Content-Type: application/json';
    }
    return newivr_keycloak_admin_request(
        $base_url . '/admin/realms/' . rawurlencode($realm) . $path,
        $method,
        $body,
        $headers
    );
}

function newivr_keycloak_user_role_for_profile($profile_id) {
    $admin_role = newivr_env('NEWIVR_KEYCLOAK_ADMIN_ROLE', 'newivr-admin');
    $agent_role = newivr_env('NEWIVR_KEYCLOAK_AGENT_ROLE', 'newivr-agente');
    $profile_id = (int)$profile_id;
    return ($profile_id === 1) ? $admin_role : $agent_role;
}

function newivr_keycloak_find_user($username) {
    $response = newivr_keycloak_admin_api('GET', '/users?username=' . rawurlencode($username) . '&exact=true', null);
    $users = json_decode($response['body'], true);
    if (!is_array($users) || empty($users)) {
        return false;
    }
    return $users[0];
}

function newivr_keycloak_role_payload($role_name) {
    $response = newivr_keycloak_admin_api('GET', '/roles/' . rawurlencode($role_name), null);
    $role = json_decode($response['body'], true);
    if (!is_array($role) || empty($role['id'])) {
        throw new Exception('Keycloak role not found: ' . $role_name);
    }
    return $role;
}

function newivr_keycloak_current_realm_roles($user_id) {
    $response = newivr_keycloak_admin_api('GET', '/users/' . rawurlencode($user_id) . '/role-mappings/realm', null);
    $roles = json_decode($response['body'], true);
    return is_array($roles) ? $roles : array();
}

function newivr_keycloak_role_mapping_payload($role) {
    return array(
        'id' => $role['id'],
        'name' => $role['name']
    );
}

function newivr_keycloak_assign_profile_role($user_id, $profile_id) {
    $config = newivr_keycloak_config();
    $admin_role = newivr_keycloak_role_payload($config['admin_role']);
    $agent_role = newivr_keycloak_role_payload($config['agent_role']);
    $desired_role = ((int)$profile_id === 1) ? $admin_role : $agent_role;
    $current_roles = newivr_keycloak_current_realm_roles($user_id);
    $remove_roles = array();
    $has_desired_role = false;

    foreach ($current_roles as $role) {
        if (!isset($role['name'])) {
            continue;
        }
        if ($role['name'] === $desired_role['name']) {
            $has_desired_role = true;
            continue;
        }
        if ($role['name'] === $admin_role['name'] || $role['name'] === $agent_role['name']) {
            $remove_roles[] = newivr_keycloak_role_mapping_payload($role);
        }
    }

    if (!empty($remove_roles)) {
        newivr_keycloak_admin_api('DELETE', '/users/' . rawurlencode($user_id) . '/role-mappings/realm', $remove_roles);
    }
    if (!$has_desired_role) {
        newivr_keycloak_admin_api('POST', '/users/' . rawurlencode($user_id) . '/role-mappings/realm', array(newivr_keycloak_role_mapping_payload($desired_role)));
    }
}

function newivr_keycloak_user_payload($username, $full_name, $email, $status) {
    $name_parts = preg_split('/\s+/', trim($full_name), 2);
    return array(
        'username' => $username,
        'enabled' => ($status === 'active'),
        'emailVerified' => true,
        'firstName' => isset($name_parts[0]) ? $name_parts[0] : $full_name,
        'lastName' => isset($name_parts[1]) ? $name_parts[1] : '',
        'email' => $email,
        'attributes' => array('newivr_status' => array($status))
    );
}

function newivr_keycloak_set_password($user_id, $password) {
    if ($password === '') {
        return;
    }
    newivr_keycloak_admin_api('PUT', '/users/' . rawurlencode($user_id) . '/reset-password', array(
        'type' => 'password',
        'value' => $password,
        'temporary' => false
    ));
}

function newivr_keycloak_create_user($username, $full_name, $email, $password, $profile_id, $status) {
    $existing = newivr_keycloak_find_user($username);
    if ($existing && isset($existing['id'])) {
        newivr_keycloak_update_user($username, $username, $full_name, $email, $password, $profile_id, $status);
        return $existing['id'];
    }

    $response = newivr_keycloak_admin_api('POST', '/users', newivr_keycloak_user_payload($username, $full_name, $email, $status));
    $location = '';
    if (preg_match('/^Location:\s*(.+)$/mi', $response['headers'], $matches)) {
        $location = trim($matches[1]);
    }
    $user_id = basename(parse_url($location, PHP_URL_PATH));
    if ($user_id === '' || $user_id === 'users') {
        $created = newivr_keycloak_find_user($username);
        if (!$created || empty($created['id'])) {
            throw new Exception('Unable to resolve created Keycloak user id');
        }
        $user_id = $created['id'];
    }
    newivr_keycloak_set_password($user_id, $password);
    newivr_keycloak_assign_profile_role($user_id, $profile_id);
    return $user_id;
}

function newivr_keycloak_update_user($old_username, $username, $full_name, $email, $password, $profile_id, $status) {
    $user = newivr_keycloak_find_user($old_username);
    if (!$user || empty($user['id'])) {
        return newivr_keycloak_create_user($username, $full_name, $email, $password, $profile_id, $status);
    }
    $user_id = $user['id'];
    newivr_keycloak_admin_api('PUT', '/users/' . rawurlencode($user_id), newivr_keycloak_user_payload($username, $full_name, $email, $status));
    newivr_keycloak_set_password($user_id, $password);
    newivr_keycloak_assign_profile_role($user_id, $profile_id);
    return $user_id;
}

function newivr_keycloak_delete_user($username) {
    $user = newivr_keycloak_find_user($username);
    if (!$user || empty($user['id'])) {
        return;
    }
    newivr_keycloak_admin_api('DELETE', '/users/' . rawurlencode($user['id']), null);
}

function newivr_require_admin_session() {
    newivr_session_start();
    if (!isset($_SESSION['profile_id']) || (int)$_SESSION['profile_id'] !== 1) {
        http_response_code(403);
        echo 'Acesso negado';
        exit;
    }
}
?>
