<?php
require_once __DIR__ . '/../keycloak_users.php';

newivr_require_admin_session();

header('Content-Type: application/json; charset=utf-8');

try {
    $user_id = isset($_GET['id']) ? (int)$_GET['id'] : 0;
    if ($user_id === 0) {
        throw new Exception('Usuario invalido');
    }
    $pdo = newivr_db_connect();
    $stmt = $pdo->prepare('SELECT id, username, full_name, email, profile_id, status FROM app_ivr_users WHERE id = :id LIMIT 1');
    $stmt->execute(array(':id' => $user_id));
    $user = $stmt->fetch(PDO::FETCH_ASSOC);
    if (!$user) {
        throw new Exception('Usuario nao encontrado');
    }
    echo json_encode(array('success' => true, 'user' => $user));
} catch (Exception $e) {
    echo json_encode(array('success' => false, 'message' => $e->getMessage()));
}
?>
