<?php
require_once __DIR__ . '/includes/keycloak_guard.php';
newivr_session_start();

try {
    $config = newivr_keycloak_config();
    $discovery = newivr_discovery();
    if (empty($config['client_secret'])) {
        throw new Exception('NEWIVR_KEYCLOAK_CLIENT_SECRET is not configured');
    }

    $_SESSION['keycloak_state'] = newivr_random_token();
    $_SESSION['keycloak_nonce'] = newivr_random_token();

    $query = http_build_query(array(
        'client_id' => $config['client_id'],
        'redirect_uri' => $config['redirect_uri'],
        'response_type' => 'code',
        'scope' => $config['scopes'],
        'state' => $_SESSION['keycloak_state'],
        'nonce' => $_SESSION['keycloak_nonce']
    ));

    newivr_redirect($discovery['authorization_endpoint'] . '?' . $query);
} catch (Exception $e) {
    error_log('NewIvr Keycloak login failed: ' . $e->getMessage());
    newivr_redirect('/NewIvr/login.php?error=KeycloakConfig&message=' . urlencode($e->getMessage()));
}
?>
