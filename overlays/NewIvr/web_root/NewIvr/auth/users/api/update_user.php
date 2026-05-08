<?php
require_once __DIR__ . '/../keycloak_users.php';
require_once __DIR__ . '/../database.php';

newivr_require_admin_session();

try {
    $user_id = isset($_POST['user_id']) ? (int)$_POST['user_id'] : 0;
    $username = sanitizeInput(isset($_POST['username']) ? $_POST['username'] : '');
    $full_name = sanitizeInput(isset($_POST['full_name']) ? $_POST['full_name'] : '');
    $email = sanitizeInput(isset($_POST['email']) ? $_POST['email'] : '');
    $password = isset($_POST['password']) ? $_POST['password'] : '';
    $profile_id = isset($_POST['profile_id']) ? (int)$_POST['profile_id'] : 0;
    $status = sanitizeInput(isset($_POST['status']) ? $_POST['status'] : 'active');

    if ($user_id === 0 || $username === '' || $full_name === '' || $email === '' || $profile_id === 0) {
        throw new Exception('Preencha todos os campos obrigatorios');
    }
    if (!validateEmail($email)) {
        throw new Exception('E-mail invalido');
    }

    $pdo = newivr_db_connect();
    $current = $pdo->prepare('SELECT username FROM app_ivr_users WHERE id = :id LIMIT 1');
    $current->execute(array(':id' => $user_id));
    $existing = $current->fetch(PDO::FETCH_ASSOC);
    if (!$existing) {
        throw new Exception('Usuario local nao encontrado');
    }

    $check = $pdo->prepare('SELECT id FROM app_ivr_users WHERE (username = :username OR email = :email) AND id <> :id LIMIT 1');
    $check->execute(array(':username' => $username, ':email' => $email, ':id' => $user_id));
    if ($check->fetch()) {
        throw new Exception('Usuario ou e-mail ja cadastrado');
    }

    newivr_keycloak_update_user($existing['username'], $username, $full_name, $email, $password, $profile_id, $status);

    $stmt = $pdo->prepare('UPDATE app_ivr_users SET username = :username, full_name = :full_name, email = :email, profile_id = :profile_id, status = :status, updated_at = NOW() WHERE id = :id');
    $stmt->execute(array(
        ':username' => $username,
        ':full_name' => $full_name,
        ':email' => $email,
        ':profile_id' => $profile_id,
        ':status' => $status,
        ':id' => $user_id
    ));

    redirectWithMessage('../index.php', 'Usuario atualizado no NewIvr e no Keycloak', 'success');
} catch (Exception $e) {
    redirectWithMessage('../index.php', $e->getMessage(), 'error');
}
?>
