<?php
require_once __DIR__ . '/includes/keycloak_guard.php';
newivr_session_start();
$config = newivr_keycloak_config();
$id_token_hint = isset($_SESSION['keycloak_id_token']) ? $_SESSION['keycloak_id_token'] : '';

$_SESSION = array();
if (ini_get('session.use_cookies')) {
    $params = session_get_cookie_params();
    setcookie(session_name(), '', time() - 42000, $params['path'], $params['domain'], $params['secure'], $params['httponly']);
}
session_destroy();

$return_to = newivr_base_url() . '/login.php';
if ($config['issuer'] !== '' && $id_token_hint !== '') {
    $logout_url = $config['issuer'] . '/protocol/openid-connect/logout?' . http_build_query(array(
        'id_token_hint' => $id_token_hint,
        'post_logout_redirect_uri' => $return_to
    ));
    newivr_redirect($logout_url);
}

newivr_redirect('/NewIvr/login.php');
?>
