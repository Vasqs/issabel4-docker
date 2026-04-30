<?php
require_once __DIR__ . '/includes/keycloak_guard.php';
newivr_session_start();

if (newivr_authenticated()) {
    $target = ((int)$_SESSION['profile_id'] === 1) ? 'index_app_ivr_admin.php' : 'index_app_ivr_agente.php';
    newivr_redirect('/NewIvr/' . $target);
}

$error = isset($_GET['error']) ? $_GET['error'] : '';
$message = isset($_GET['message']) ? $_GET['message'] : '';
$error_messages = array(
    'KeycloakConfig' => 'Autenticacao Keycloak nao configurada.',
    'KeycloakCallback' => 'Falha ao validar o retorno do Keycloak.',
    'AcessoNegado' => 'Acesso negado. Usuario sem permissao no NewIvr.',
    'SessaoExpirada' => 'Sua sessao expirou. Entre novamente.',
    'SessaoInvalida' => 'Sessao invalida. Entre novamente.'
);
if ($message === '' && isset($error_messages[$error])) {
    $message = $error_messages[$error];
}

if ($message === '' && $error === '' && !isset($_GET['manual'])) {
    require __DIR__ . '/keycloak_login.php';
    exit;
}
?>
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NewIvr - Login</title>
    <style>
        * { box-sizing: border-box; }
        body {
            margin: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: Arial, Helvetica, sans-serif;
            background: #111827;
            color: #f8fafc;
        }
        .login-box {
            width: min(420px, calc(100vw - 32px));
            padding: 32px;
            background: #1f2937;
            border: 1px solid rgba(255,255,255,.12);
            border-radius: 8px;
            box-shadow: 0 24px 70px rgba(0,0,0,.35);
        }
        h1 {
            margin: 0 0 8px;
            font-size: 28px;
            line-height: 1.15;
            letter-spacing: 0;
        }
        p {
            margin: 0 0 24px;
            color: #cbd5e1;
            line-height: 1.45;
        }
        .alert {
            margin-bottom: 20px;
            padding: 12px 14px;
            border: 1px solid rgba(248,113,113,.35);
            background: rgba(127,29,29,.35);
            color: #fecaca;
            border-radius: 6px;
            font-size: 14px;
            line-height: 1.35;
        }
        .login-btn {
            display: inline-flex;
            width: 100%;
            min-height: 48px;
            align-items: center;
            justify-content: center;
            padding: 12px 16px;
            border: 0;
            border-radius: 6px;
            background: #2563eb;
            color: white;
            text-decoration: none;
            font-size: 16px;
            font-weight: 700;
        }
        .login-btn:hover { background: #1d4ed8; }
        .meta {
            margin-top: 18px;
            color: #94a3b8;
            font-size: 13px;
        }
    </style>
</head>
<body>
    <main class="login-box">
        <h1>NewIvr</h1>
        <p>Acesso protegido por Keycloak.</p>
        <?php if ($message !== ''): ?>
            <div class="alert"><?php echo htmlspecialchars($message, ENT_QUOTES, 'UTF-8'); ?></div>
        <?php endif; ?>
        <a class="login-btn" href="keycloak_login.php">Entrar com Keycloak</a>
        <div class="meta">Usuarios precisam existir em app_ivr_users e possuir role newivr-admin ou newivr-agente.</div>
    </main>
</body>
</html>
