<?php
require_once __DIR__ . '/../keycloak_users.php';
require_once __DIR__ . '/../database.php';

newivr_require_admin_session();

try {
    $user_id = isset($_GET['id']) ? (int)$_GET['id'] : 0;
    if ($user_id === 0) {
        throw new Exception('Usuario invalido');
    }
    if (isset($_SESSION['user_id']) && (int)$_SESSION['user_id'] === $user_id) {
        throw new Exception('Nao e possivel excluir o proprio usuario');
    }

    $pdo = newivr_db_connect();
    $stmt = $pdo->prepare('SELECT username FROM app_ivr_users WHERE id = :id LIMIT 1');
    $stmt->execute(array(':id' => $user_id));
    $user = $stmt->fetch(PDO::FETCH_ASSOC);
    if (!$user) {
        throw new Exception('Usuario local nao encontrado');
    }

    newivr_keycloak_delete_user($user['username']);

    $delete = $pdo->prepare('DELETE FROM app_ivr_users WHERE id = :id');
    $delete->execute(array(':id' => $user_id));

    redirectWithMessage('../index.php', 'Usuario removido do NewIvr e do Keycloak', 'success');
} catch (Exception $e) {
    redirectWithMessage('../index.php', $e->getMessage(), 'error');
}
?>
