<?php
require_once __DIR__ . '/includes/keycloak_guard.php';
header('Content-Type: application/json; charset=utf-8');

if (newivr_authenticated()) {
    $target = ((int)$_SESSION['profile_id'] === 1) ? 'index_app_ivr_admin.php' : 'index_app_ivr_agente.php';
    echo json_encode(array(
        'success' => true,
        'auth_provider' => 'Keycloak',
        'username' => isset($_SESSION['username']) ? $_SESSION['username'] : '',
        'profile_id' => isset($_SESSION['profile_id']) ? (int)$_SESSION['profile_id'] : 0,
        'redirect_url' => $target
    ));
    exit;
}

echo json_encode(array(
    'success' => false,
    'auth_provider' => 'Keycloak',
    'error' => 'password_login_disabled',
    'message' => 'Autenticacao local por senha foi desativada. Use o login Keycloak.',
    'redirect_url' => 'keycloak_login.php'
));
?>
