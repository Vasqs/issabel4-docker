<?php
require_once __DIR__ . '/includes/keycloak_guard.php';
newivr_session_start();

try {
    if (isset($_GET['error'])) {
        throw new Exception('Keycloak returned error: ' . $_GET['error']);
    }
    if (!isset($_GET['code']) || !isset($_GET['state'])) {
        throw new Exception('Missing authorization code or state');
    }
    if (!isset($_SESSION['keycloak_state']) || $_GET['state'] !== $_SESSION['keycloak_state']) {
        throw new Exception('Invalid Keycloak state');
    }

    $config = newivr_keycloak_config();
    $discovery = newivr_discovery();
    $body = http_build_query(array(
        'grant_type' => 'authorization_code',
        'code' => $_GET['code'],
        'redirect_uri' => $config['redirect_uri'],
        'client_id' => $config['client_id'],
        'client_secret' => $config['client_secret']
    ));

    $token_response = newivr_http_request(
        $discovery['token_endpoint'],
        'POST',
        $body,
        array('Content-Type: application/x-www-form-urlencoded')
    );
    $tokens = json_decode($token_response, true);
    if (!is_array($tokens) || empty($tokens['id_token']) || empty($tokens['access_token'])) {
        throw new Exception('Invalid token response from Keycloak');
    }

    $id_claims = newivr_verify_jwt($tokens['id_token'], $discovery['jwks_uri']);
    $access_claims = newivr_verify_jwt($tokens['access_token'], $discovery['jwks_uri']);
    if (isset($id_claims['nonce']) && isset($_SESSION['keycloak_nonce']) && $id_claims['nonce'] !== $_SESSION['keycloak_nonce']) {
        throw new Exception('Invalid Keycloak nonce');
    }

    unset($_SESSION['keycloak_state']);
    unset($_SESSION['keycloak_nonce']);

    $profile_id = newivr_establish_session($id_claims, $access_claims, $tokens['id_token']);
    $target = ($profile_id === 1) ? 'index_app_ivr_admin.php' : 'index_app_ivr_agente.php';
    newivr_redirect('/NewIvr/' . $target);
} catch (Exception $e) {
    error_log('NewIvr Keycloak callback failed: ' . $e->getMessage());
    newivr_redirect('/NewIvr/login.php?error=AcessoNegado&message=' . urlencode($e->getMessage()));
}
?>
