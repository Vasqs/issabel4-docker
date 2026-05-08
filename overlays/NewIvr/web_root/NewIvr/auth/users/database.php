<?php
/**
 * Configuração de conexão com o banco de dados
 * Compatível com PHP 5 e MariaDB 5.5
 */

require_once dirname(dirname(__DIR__)) . '/includes/keycloak_guard.php';

class Database {
    private $host = 'localhost';
    private $db_name = 'call_center';
    private $username = 'asterisk';
    private $password = 'asterisk';
    public $conn;

    public function getConnection() {
        $this->conn = null;

        try {
            if (function_exists('newivr_db_config')) {
                $config = newivr_db_config();
                $this->host = $config['host'];
                $this->db_name = $config['name'];
                $this->username = $config['user'];
                $this->password = $config['pass'];
            }
            // Para PHP 5 e MariaDB 5.5
            $this->conn = new PDO(
                "mysql:host=" . $this->host . ";dbname=" . $this->db_name,
                $this->username,
                $this->password
            );

            // Configurar para lançar exceções em caso de erro
            $this->conn->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
            // Usar UTF-8
            $this->conn->exec("SET NAMES 'utf8'");

        } catch(PDOException $exception) {
            die("Erro de conexão: " . $exception->getMessage());
        }

        return $this->conn;
    }
}

// Função para redirecionar com mensagem
function redirectWithMessage($url, $message, $type = 'success') {
    session_start();
    $_SESSION['alert_message'] = $message;
    $_SESSION['alert_type'] = $type;
    header("Location: $url");
    exit();
}

// Função para validar email
function validateEmail($email) {
    return filter_var($email, FILTER_VALIDATE_EMAIL);
}

// Função para validar entrada
function sanitizeInput($data) {
    $data = trim($data);
    $data = stripslashes($data);
    $data = htmlspecialchars($data);
    return $data;
}

// Iniciar sessão se não estiver iniciada
if (session_id() == '') {
    session_start();
}
?>
