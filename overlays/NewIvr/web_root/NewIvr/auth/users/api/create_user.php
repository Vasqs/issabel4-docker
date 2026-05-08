<?php
require_once __DIR__ . '/../keycloak_users.php';
require_once __DIR__ . '/../database.php';

newivr_require_admin_session();

try {
    $username = sanitizeInput(isset($_POST['username']) ? $_POST['username'] : '');
    $full_name = sanitizeInput(isset($_POST['full_name']) ? $_POST['full_name'] : '');
    $email = sanitizeInput(isset($_POST['email']) ? $_POST['email'] : '');
    $password = isset($_POST['password']) ? $_POST['password'] : '';
    $profile_id = isset($_POST['profile_id']) ? (int)$_POST['profile_id'] : 0;
    $status = sanitizeInput(isset($_POST['status']) ? $_POST['status'] : 'active');

    if ($username === '' || $full_name === '' || $email === '' || $password === '' || $profile_id === 0) {
        throw new Exception('Preencha todos os campos obrigatorios');
    }
    if (!validateEmail($email)) {
        throw new Exception('E-mail invalido');
    }

    $pdo = newivr_db_connect();
    $check = $pdo->prepare('SELECT id FROM app_ivr_users WHERE username = :username OR email = :email LIMIT 1');
    $check->execute(array(':username' => $username, ':email' => $email));
    if ($check->fetch()) {
        throw new Exception('Usuario ou e-mail ja cadastrado');
    }

    newivr_keycloak_create_user($username, $full_name, $email, $password, $profile_id, $status);

    $stmt = $pdo->prepare("INSERT INTO app_ivr_users (username, password, full_name, email, profile_id, status, created_at, updated_at) VALUES (:username, 'keycloak', :full_name, :email, :profile_id, :status, NOW(), NOW())");
    $stmt->execute(array(
        ':username' => $username,
        ':full_name' => $full_name,
        ':email' => $email,
        ':profile_id' => $profile_id,
        ':status' => $status
    ));

    redirectWithMessage('../index.php', 'Usuario sincronizado com Keycloak', 'success');
} catch (Exception $e) {
    redirectWithMessage('../index.php', $e->getMessage(), 'error');
}
?>
