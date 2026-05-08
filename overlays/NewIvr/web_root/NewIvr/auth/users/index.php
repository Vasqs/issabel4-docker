<?php
// Iniciar sessão para mensagens de feedback
session_start();

// Verificar se há mensagens da sessão
$alert_message = '';
$alert_type = '';

if (isset($_SESSION['alert_message'])) {
    $alert_message = $_SESSION['alert_message'];
    $alert_type = $_SESSION['alert_type'];
    unset($_SESSION['alert_message']);
    unset($_SESSION['alert_type']);
}

// Carregar conexão com o banco
require_once __DIR__ . '/database.php';
$database = new Database();
$db = $database->getConnection();

// Buscar perfis da tabela app_ivr_profiles
$profiles = [];
$profiles_error = '';
try {
    $profileQuery = "SELECT id, name, description FROM app_ivr_profiles ORDER BY name";
    $profileStmt = $db->prepare($profileQuery);
    $profileStmt->execute();
    $profiles = $profileStmt->fetchAll(PDO::FETCH_ASSOC);

    if (empty($profiles)) {
        $profiles_error = "Nenhum perfil encontrado na tabela app_ivr_profiles. É necessário criar perfis primeiro.";
    }
} catch (PDOException $e) {
    $profiles_error = "Erro ao carregar perfis: " . $e->getMessage();
}

// Buscar usuários
$users = [];
$search = isset($_GET['search']) ? $_GET['search'] : '';

try {
    $query = "SELECT
                u.id,
                u.username,
                u.full_name,
                u.email,
                u.profile_id,
                u.status,
                u.last_login,
                u.created_at,
                u.updated_at,
                p.name as profile_name
              FROM app_ivr_users u
              LEFT JOIN app_ivr_profiles p ON u.profile_id = p.id";

    if (!empty($search)) {
        $query .= " WHERE u.username LIKE :search
                    OR u.full_name LIKE :search
                    OR u.email LIKE :search
                    OR p.name LIKE :search";
    }

    $query .= " ORDER BY u.id DESC";

    $stmt = $db->prepare($query);

    if (!empty($search)) {
        $search_param = "%" . $search . "%";
        $stmt->bindParam(':search', $search_param);
    }

    $stmt->execute();
    $users = $stmt->fetchAll(PDO::FETCH_ASSOC);

} catch (PDOException $e) {
    $users_error = "Erro ao carregar usuários: " . $e->getMessage();
}
?>
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gerenciamento de Usuários IVR</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }

        body {
            background-color: #f5f7fa;
            color: #333;
            padding: 20px;
            line-height: 1.6;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            border-radius: 12px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08);
            overflow: hidden;
        }

        header {
            background: linear-gradient(135deg, #6a11cb 0%, #2575fc 100%);
            color: white;
            padding: 25px 30px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }

        header h1 {
            font-size: 28px;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 12px;
        }

        header p {
            opacity: 0.9;
            font-size: 16px;
        }

        .main-content {
            display: flex;
            flex-direction: column;
            min-height: 600px;
        }

        .toolbar {
            padding: 20px 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background-color: #f9fafc;
            border-bottom: 1px solid #eaeef2;
        }

        .btn {
            padding: 12px 24px;
            border-radius: 8px;
            border: none;
            font-weight: 600;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            transition: all 0.3s ease;
            font-size: 15px;
        }

        .btn-primary {
            background-color: #4a6ee0;
            color: white;
        }

        .btn-primary:hover {
            background-color: #3a5ed0;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(58, 94, 208, 0.2);
        }

        .btn-secondary {
            background-color: #6c757d;
            color: white;
        }

        .btn-danger {
            background-color: #e74c3c;
            color: white;
        }

        .btn-success {
            background-color: #2ecc71;
            color: white;
        }

        .search-box {
            position: relative;
            width: 300px;
        }

        .search-box input {
            width: 100%;
            padding: 12px 20px 12px 45px;
            border-radius: 8px;
            border: 1px solid #ddd;
            font-size: 15px;
            transition: all 0.3s;
        }

        .search-box input:focus {
            outline: none;
            border-color: #4a6ee0;
            box-shadow: 0 0 0 3px rgba(74, 110, 224, 0.1);
        }

        .search-box i {
            position: absolute;
            left: 15px;
            top: 50%;
            transform: translateY(-50%);
            color: #888;
        }

        .table-container {
            padding: 0 30px 30px;
            flex: 1;
            overflow-x: auto;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }

        thead {
            background-color: #f1f5f9;
        }

        th {
            padding: 16px 15px;
            text-align: left;
            font-weight: 600;
            color: #475569;
            border-bottom: 2px solid #e2e8f0;
            font-size: 15px;
        }

        td {
            padding: 16px 15px;
            border-bottom: 1px solid #e2e8f0;
            color: #475569;
        }

        tr:hover {
            background-color: #f8fafc;
        }

        .status {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 50px;
            font-size: 13px;
            font-weight: 600;
        }

        .status-active {
            background-color: #d1fae5;
            color: #065f46;
        }

        .status-inactive {
            background-color: #fee2e2;
            color: #991b1b;
        }

        .status-blocked {
            background-color: #fef3c7;
            color: #92400e;
        }

        .actions {
            display: flex;
            gap: 8px;
        }

        .action-btn {
            width: 36px;
            height: 36px;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.2s;
            border: none;
            color: white;
        }

        .edit-btn {
            background-color: #3b82f6;
        }

        .delete-btn {
            background-color: #ef4444;
        }

        .edit-btn:hover {
            background-color: #2563eb;
        }

        .delete-btn:hover {
            background-color: #dc2626;
        }

        .no-data {
            text-align: center;
            padding: 50px 20px;
            color: #94a3b8;
        }

        .no-data i {
            font-size: 48px;
            margin-bottom: 15px;
            color: #cbd5e1;
        }

        /* Modal Styles */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
            z-index: 1000;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }

        .modal-content {
            background-color: white;
            border-radius: 12px;
            width: 100%;
            max-width: 700px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            animation: modalAppear 0.3s ease-out;
        }

        @keyframes modalAppear {
            from {
                opacity: 0;
                transform: translateY(-30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .modal-header {
            padding: 24px 30px;
            border-bottom: 1px solid #eaeef2;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .modal-header h2 {
            font-size: 22px;
            color: #1e293b;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .close-modal {
            background: none;
            border: none;
            font-size: 24px;
            color: #94a3b8;
            cursor: pointer;
            transition: color 0.2s;
        }

        .close-modal:hover {
            color: #475569;
        }

        .modal-body {
            padding: 30px;
            max-height: 70vh;
            overflow-y: auto;
        }

        .form-row {
            display: flex;
            flex-wrap: wrap;
            margin: 0 -15px;
        }

        .form-group {
            flex: 1 0 50%;
            padding: 0 15px;
            margin-bottom: 24px;
            min-width: 250px;
        }

        .form-group.full-width {
            flex: 1 0 100%;
        }

        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #475569;
        }

        .form-control {
            width: 100%;
            padding: 12px 16px;
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            font-size: 15px;
            transition: all 0.3s;
        }

        .form-control:focus {
            outline: none;
            border-color: #4a6ee0;
            box-shadow: 0 0 0 3px rgba(74, 110, 224, 0.1);
        }

        .form-footer {
            padding: 20px 30px;
            border-top: 1px solid #eaeef2;
            display: flex;
            justify-content: flex-end;
            gap: 12px;
        }

        .password-toggle {
            position: absolute;
            right: 15px;
            top: 50%;
            transform: translateY(-50%);
            background: none;
            border: none;
            color: #64748b;
            cursor: pointer;
        }

        .password-container {
            position: relative;
        }

        .password-container input {
            padding-right: 45px;
        }

        .loading {
            text-align: center;
            padding: 40px;
            color: #64748b;
        }

        .loading i {
            font-size: 40px;
            margin-bottom: 15px;
            color: #4a6ee0;
        }

        .alert {
            padding: 15px 20px;
            border-radius: 8px;
            margin: 20px 30px 0 30px;
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .alert-success {
            background-color: #d1fae5;
            color: #065f46;
            border: 1px solid #a7f3d0;
        }

        .alert-error {
            background-color: #fee2e2;
            color: #991b1b;
            border: 1px solid #fecaca;
        }

        .alert-warning {
            background-color: #fef3c7;
            color: #92400e;
            border: 1px solid #fde68a;
        }

        .alert-info {
            background-color: #dbeafe;
            color: #1e40af;
            border: 1px solid #93c5fd;
        }

        .connection-status {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            border-radius: 50px;
            font-size: 14px;
            font-weight: 500;
            background-color: #f1f5f9;
            margin-top: 10px;
        }

        .connected {
            color: #10b981;
        }

        .disconnected {
            color: #ef4444;
        }

        footer {
            padding: 20px 30px;
            text-align: center;
            color: #64748b;
            font-size: 14px;
            border-top: 1px solid #eaeef2;
            background-color: #f9fafc;
        }

        /* Estilos para o select de perfis */
        .profile-option {
            display: flex;
            flex-direction: column;
            padding: 8px 0;
        }

        .profile-name {
            font-weight: 600;
            color: #1e293b;
        }

        .profile-description {
            font-size: 12px;
            color: #64748b;
            margin-top: 2px;
            font-style: italic;
        }

        .no-profiles {
            background-color: #fef3c7;
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
            border: 1px solid #fde68a;
        }

        @media (max-width: 768px) {
            .toolbar {
                flex-direction: column;
                gap: 15px;
                align-items: stretch;
            }

            .search-box {
                width: 100%;
            }

            .form-group {
                flex: 1 0 100%;
            }

            .table-container {
                padding: 0 15px 20px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1><i class="fas fa-users-cog"></i> Gerenciamento de Usuários IVR</h1>
            <p>Gerencie usuários do sistema de IVR com sincronização Keycloak - Banco: call_center | Tabela: app_ivr_users</p>
            <div class="connection-status <?php echo !empty($profiles_error) ? 'disconnected' : 'connected'; ?>" id="connectionStatus">
                <i class="fas fa-database"></i>
                <span id="connectionText">
                    <?php
                    if (!empty($profiles_error)) {
                        echo "Erro: " . $profiles_error;
                    } else {
                        echo "Conectado | " . count($profiles) . " perfis disponíveis";
                    }
                    ?>
                </span>
            </div>
        </header>

        <div class="main-content">
            <?php if ($alert_message): ?>
            <div class="alert alert-<?php echo $alert_type; ?>">
                <i class="fas fa-<?php echo $alert_type == 'success' ? 'check-circle' : ($alert_type == 'error' ? 'exclamation-circle' : 'exclamation-triangle'); ?>"></i>
                <span><?php echo htmlspecialchars($alert_message); ?></span>
            </div>
            <?php endif; ?>

            <?php if (!empty($profiles_error)): ?>
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle"></i>
                <span>
                    <?php echo htmlspecialchars($profiles_error); ?>
                    <br>
                    <small><a href="testar_perfis.php" style="color: inherit; text-decoration: underline;">Clique aqui para diagnosticar o problema</a></small>
                </span>
            </div>
            <?php endif; ?>

            <div class="toolbar">
                <form method="GET" action="" style="display: contents;">
                    <div class="search-box">
                        <i class="fas fa-search"></i>
                        <input type="text" name="search" id="searchInput" placeholder="Buscar usuários..."
                               value="<?php echo isset($_GET['search']) ? htmlspecialchars($_GET['search']) : ''; ?>">
                    </div>
                </form>
                <button class="btn btn-primary" id="addUserBtn" <?php echo empty($profiles) ? 'disabled' : ''; ?>>
                    <i class="fas fa-user-plus"></i> Novo Usuário
                </button>
            </div>

            <div class="table-container">
                <div id="loadingIndicator" class="loading" style="display: none;">
                    <i class="fas fa-spinner fa-spin"></i>
                    <p>Carregando usuários...</p>
                </div>

                <table id="usersTable">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Usuário</th>
                            <th>Nome Completo</th>
                            <th>E-mail</th>
                            <th>Perfil</th>
                            <th>Status</th>
                            <th>Último Login</th>
                            <th>Criado em</th>
                            <th>Ações</th>
                        </tr>
                    </thead>
                    <tbody id="usersTableBody">
                        <?php if (isset($users_error)): ?>
                        <tr>
                            <td colspan="9" style="text-align: center; padding: 40px;">
                                <div class="no-data">
                                    <i class="fas fa-exclamation-circle"></i>
                                    <h3>Erro ao carregar usuários</h3>
                                    <p><?php echo htmlspecialchars($users_error); ?></p>
                                </div>
                            </td>
                        </tr>
                        <?php elseif (count($users) > 0): ?>
                            <?php foreach ($users as $user): ?>
                                <?php
                                // Determinar classe de status
                                $status_class = '';
                                $status_text = '';

                                switch($user['status']) {
                                    case 'active':
                                        $status_class = 'status-active';
                                        $status_text = 'Ativo';
                                        break;
                                    case 'inactive':
                                        $status_class = 'status-inactive';
                                        $status_text = 'Inativo';
                                        break;
                                    case 'blocked':
                                        $status_class = 'status-blocked';
                                        $status_text = 'Bloqueado';
                                        break;
                                    default:
                                        $status_class = 'status-inactive';
                                        $status_text = 'Inativo';
                                }

                                // Formatar data do último login
                                $last_login = $user['last_login'] ?
                                    date('d/m/Y H:i', strtotime($user['last_login'])) :
                                    'Nunca';

                                // Formatar data de criação
                                $created_at = $user['created_at'] ?
                                    date('d/m/Y', strtotime($user['created_at'])) :
                                    'N/A';
                                ?>
                                <tr>
                                    <td><?php echo $user['id']; ?></td>
                                    <td><strong><?php echo htmlspecialchars($user['username']); ?></strong></td>
                                    <td><?php echo htmlspecialchars($user['full_name']); ?></td>
                                    <td><?php echo htmlspecialchars($user['email']); ?></td>
                                    <td>
                                        <div>
                                            <?php echo !empty($user['profile_name']) ? htmlspecialchars($user['profile_name']) : 'Perfil ' . $user['profile_id']; ?>
                                            <?php if (!empty($user['profile_name'])): ?>
                                            <div style="font-size: 11px; color: #6c757d;">ID: <?php echo $user['profile_id']; ?></div>
                                            <?php endif; ?>
                                        </div>
                                    </td>
                                    <td><span class="status <?php echo $status_class; ?>"><?php echo $status_text; ?></span></td>
                                    <td><?php echo $last_login; ?></td>
                                    <td><?php echo $created_at; ?></td>
                                    <td>
                                        <div class="actions">
                                            <button class="action-btn edit-btn" onclick="openUserModal(<?php echo $user['id']; ?>)" title="Editar" <?php echo empty($profiles) ? 'disabled' : ''; ?>>
                                                <i class="fas fa-edit"></i>
                                            </button>
                                            <button class="action-btn delete-btn" onclick="confirmDelete(<?php echo $user['id']; ?>, '<?php echo htmlspecialchars($user['username'], ENT_QUOTES); ?>')" title="Excluir">
                                                <i class="fas fa-trash"></i>
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            <?php endforeach; ?>
                        <?php else: ?>
                        <tr>
                            <td colspan="9" style="text-align: center; padding: 40px;">
                                <div class="no-data">
                                    <i class="fas fa-user-slash"></i>
                                    <h3>Nenhum usuário encontrado</h3>
                                    <p>Clique em "Novo Usuário" para adicionar um usuário ao sistema.</p>
                                </div>
                            </td>
                        </tr>
                        <?php endif; ?>
                    </tbody>
                </table>
            </div>
        </div>

        <footer>
            <p>Sistema de Gerenciamento de Usuários IVR &copy; <?php echo date('Y'); ?> | Banco: call_center | Identidade: Keycloak</p>
            <p style="font-size: 12px; margin-top: 5px;">
                PHP <?php echo phpversion(); ?> | MariaDB 5.5 |
                Perfis: <?php echo count($profiles); ?> |
                Usuários: <?php echo count($users); ?>
            </p>
        </footer>
    </div>

    <!-- Modal para adicionar/editar usuário -->
    <div class="modal" id="userModal">
        <div class="modal-content">
            <div class="modal-header">
                <h2><i class="fas fa-user-edit"></i> <span id="modalTitle">Novo Usuário</span></h2>
                <button class="close-modal" id="closeModal">&times;</button>
            </div>

            <div class="modal-body">
                <form id="userForm" method="POST" action="api/create_user.php">
                    <div class="form-row">
                        <div class="form-group">
                            <label for="username">Nome de Usuário *</label>
                            <input type="text" id="username" name="username" class="form-control" required>
                            <small class="form-text">Deve ser único no sistema</small>
                        </div>

                        <div class="form-group">
                            <label for="full_name">Nome Completo *</label>
                            <input type="text" id="full_name" name="full_name" class="form-control" required>
                        </div>

                        <div class="form-group">
                            <label for="email">E-mail *</label>
                            <input type="email" id="email" name="email" class="form-control" required>
                            <small class="form-text">Deve ser único no sistema</small>
                        </div>

                        <div class="form-group password-container">
                            <label for="password">Senha <span id="passwordRequired">*</span></label>
                            <input type="password" id="password" name="password" class="form-control">
                            <button type="button" class="password-toggle" id="togglePassword">
                                <i class="fas fa-eye"></i>
                            </button>
                            <small class="form-text" id="passwordHelp">Deixe em branco para manter a senha atual</small>
                        </div>

                        <div class="form-group full-width">
                            <label for="profile_id">Perfil *</label>
                            <?php if (empty($profiles)): ?>
                            <div class="no-profiles">
                                <i class="fas fa-exclamation-triangle"></i>
                                Nenhum perfil disponível. Crie perfis na tabela app_ivr_profiles primeiro.
                            </div>
                            <input type="hidden" id="profile_id" name="profile_id" value="">
                            <?php else: ?>
                            <select id="profile_id" name="profile_id" class="form-control" required>
                                <option value="">-- Selecione um perfil --</option>
                                <?php foreach ($profiles as $profile): ?>
                                    <option value="<?php echo $profile['id']; ?>">
                                        <div class="profile-option">
                                            <span class="profile-name"><?php echo htmlspecialchars($profile['name']); ?></span>
                                            <?php if (!empty($profile['description'])): ?>
                                            <span class="profile-description"><?php echo htmlspecialchars($profile['description']); ?></span>
                                            <?php endif; ?>
                                        </div>
                                    </option>
                                <?php endforeach; ?>
                            </select>
                            <?php endif; ?>
                            <small class="form-text">Selecione o perfil de acesso do usuário</small>
                        </div>

                        <div class="form-group">
                            <label for="status">Status</label>
                            <select id="status" name="status" class="form-control">
                                <option value="active">Ativo</option>
                                <option value="inactive">Inativo</option>
                                <option value="blocked">Bloqueado</option>
                            </select>
                        </div>
                    </div>

                    <input type="hidden" id="user_id" name="user_id">
                    <input type="hidden" id="action_type" name="action_type" value="create">
                </form>
            </div>

            <div class="form-footer">
                <button class="btn btn-secondary" id="cancelBtn">Cancelar</button>
                <button class="btn btn-success" id="saveUserBtn" <?php echo empty($profiles) ? 'disabled' : ''; ?>>
                    <i class="fas fa-save"></i> Salvar Usuário
                </button>
            </div>
        </div>
    </div>

    <!-- Modal de confirmação para exclusão -->
    <div class="modal" id="confirmModal">
        <div class="modal-content" style="max-width: 500px;">
            <div class="modal-header">
                <h2><i class="fas fa-exclamation-triangle"></i> Confirmar Exclusão</h2>
                <button class="close-modal" id="closeConfirmModal">&times;</button>
            </div>

            <div class="modal-body">
                <p>Tem certeza que deseja excluir o usuário <strong id="userToDeleteName"></strong>?</p>
                <p>Esta ação não pode ser desfeita.</p>
            </div>

            <div class="form-footer">
                <button class="btn btn-secondary" id="cancelDeleteBtn">Cancelar</button>
                <a href="" id="confirmDeleteLink" class="btn btn-danger">
                    <i class="fas fa-trash"></i> Excluir Usuário
                </a>
            </div>
        </div>
    </div>

    <script>
        // Elementos DOM
        const usersTable = document.getElementById('usersTable');
        const loadingIndicator = document.getElementById('loadingIndicator');
        const searchInput = document.getElementById('searchInput');
        const addUserBtn = document.getElementById('addUserBtn');
        const userModal = document.getElementById('userModal');
        const confirmModal = document.getElementById('confirmModal');
        const closeModalBtn = document.getElementById('closeModal');
        const closeConfirmModalBtn = document.getElementById('closeConfirmModal');
        const cancelBtn = document.getElementById('cancelBtn');
        const cancelDeleteBtn = document.getElementById('cancelDeleteBtn');
        const saveUserBtn = document.getElementById('saveUserBtn');
        const userForm = document.getElementById('userForm');
        const modalTitle = document.getElementById('modalTitle');
        const passwordToggle = document.getElementById('togglePassword');
        const passwordField = document.getElementById('password');
        const passwordRequired = document.getElementById('passwordRequired');
        const passwordHelp = document.getElementById('passwordHelp');
        const connectionText = document.getElementById('connectionText');
        const connectionStatus = document.getElementById('connectionStatus');
        const actionType = document.getElementById('action_type');
        const userIdField = document.getElementById('user_id');
        const confirmDeleteLink = document.getElementById('confirmDeleteLink');

        // Esconder loading indicator e mostrar tabela
        document.addEventListener('DOMContentLoaded', function() {
            // Verificar conexão
            const hasUsers = document.querySelectorAll('#usersTableBody tr').length > 0;
            const hasProfiles = <?php echo count($profiles) > 0 ? 'true' : 'false'; ?>;

            if (hasUsers && hasProfiles) {
                connectionStatus.className = 'connection-status connected';
                connectionText.textContent = 'Conectado ao banco de dados';
            } else if (!hasProfiles) {
                connectionStatus.className = 'connection-status disconnected';
                connectionText.textContent = 'Sem perfis disponíveis';
                addUserBtn.disabled = true;
                saveUserBtn.disabled = true;
            }

            // Configurar eventos
            addUserBtn.addEventListener('click', () => openUserModal());
            closeModalBtn.addEventListener('click', () => closeUserModal());
            closeConfirmModalBtn.addEventListener('click', () => closeConfirmModal());
            cancelBtn.addEventListener('click', () => closeUserModal());
            cancelDeleteBtn.addEventListener('click', () => closeConfirmModal());
            saveUserBtn.addEventListener('click', () => saveUser());

            // Busca em tempo real (para evitar submit do form)
            searchInput.addEventListener('keyup', function(e) {
                if (e.key === 'Enter') {
                    this.form.submit();
                }
            });

            // Alternar visibilidade da senha
            if (passwordToggle) {
                passwordToggle.addEventListener('click', () => {
                    const type = passwordField.getAttribute('type') === 'password' ? 'text' : 'password';
                    passwordField.setAttribute('type', type);
                    passwordToggle.innerHTML = type === 'password' ? '<i class="fas fa-eye"></i>' : '<i class="fas fa-eye-slash"></i>';
                });
            }

            // Fechar modais ao clicar fora
            window.addEventListener('click', (event) => {
                if (event.target === userModal) closeUserModal();
                if (event.target === confirmModal) closeConfirmModal();
            });
        });

        // Funções do modal de usuário
        function openUserModal(userId = null) {
            if (userId) {
                // Modo edição - carregar dados do usuário via AJAX
                modalTitle.textContent = 'Editar Usuário';
                passwordRequired.style.display = 'none';
                passwordHelp.textContent = 'Deixe em branco para manter a senha atual';
                actionType.value = 'update';
                userIdField.value = userId;

                // Carregar dados do usuário
                fetch(`api/get_user.php?id=${userId}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            const user = data.user;
                            document.getElementById('username').value = user.username;
                            document.getElementById('full_name').value = user.full_name;
                            document.getElementById('email').value = user.email;
                            document.getElementById('profile_id').value = user.profile_id;
                            document.getElementById('status').value = user.status;
                            document.getElementById('password').value = '';

                            // Atualizar action do formulário
                            userForm.action = 'api/update_user.php';
                        } else {
                            alert('Erro ao carregar usuário: ' + data.message);
                        }
                    })
                    .catch(error => {
                        console.error('Erro:', error);
                        alert('Erro ao carregar usuário');
                    });
            } else {
                // Modo criação
                modalTitle.textContent = 'Novo Usuário';
                passwordRequired.style.display = 'inline';
                passwordHelp.textContent = '';
                actionType.value = 'create';
                userIdField.value = '';
                userForm.reset();
                document.getElementById('status').value = 'active';

                // Atualizar action do formulário
                userForm.action = 'api/create_user.php';
            }

            userModal.style.display = 'flex';
        }

        function closeUserModal() {
            userModal.style.display = 'none';
        }

        // Funções do modal de confirmação
        function confirmDelete(userId, username) {
            document.getElementById('userToDeleteName').textContent = username;
            confirmDeleteLink.href = `api/delete_user.php?id=${userId}`;
            confirmModal.style.display = 'flex';
        }

        function closeConfirmModal() {
            confirmModal.style.display = 'none';
        }

        // Função para salvar usuário via AJAX
        function saveUser() {
            const formData = new FormData(userForm);

            // Validações básicas
            const username = document.getElementById('username').value.trim();
            const full_name = document.getElementById('full_name').value.trim();
            const email = document.getElementById('email').value.trim();
            const profile_id = document.getElementById('profile_id').value;
            const password = document.getElementById('password').value;
            const action = actionType.value;

            if (!username || !full_name || !email || !profile_id) {
                alert('Por favor, preencha todos os campos obrigatórios.');
                return;
            }

            if (action === 'create' && !password) {
                alert('Para criar um novo usuário, é necessário definir uma senha.');
                return;
            }

            // Enviar formulário
            userForm.submit();
        }
    </script>
</body>
</html>
