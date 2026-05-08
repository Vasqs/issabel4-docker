import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NEWIVR_ROOT = ROOT / "overlays" / "NewIvr" / "web_root" / "NewIvr"


def read_legacy_text(path: Path) -> str:
    return path.read_text(encoding="latin-1")


class NewIvrKeycloakAuthTests(unittest.TestCase):
    def test_root_htaccess_auto_prepends_keycloak_guard_for_all_php(self) -> None:
        htaccess = NEWIVR_ROOT / ".htaccess"
        self.assertTrue(htaccess.exists(), "NewIvr must protect direct PHP entrypoints with .htaccess")

        text = htaccess.read_text()
        self.assertIn("auto_prepend_file", text)
        self.assertIn("includes/keycloak_guard.php", text)

        apache_conf = ROOT / "docker" / "issabel" / "rootfs" / "etc" / "httpd" / "conf.d" / "newivr-htaccess.conf"
        self.assertTrue(apache_conf.exists(), "Apache must allow NewIvr to read its .htaccess guard")
        apache_text = apache_conf.read_text()
        self.assertIn('/var/www/html/NewIvr', apache_text)
        self.assertIn('AllowOverride All', apache_text)

    def test_keycloak_guard_declares_public_allowlist_and_role_mapping(self) -> None:
        guard = NEWIVR_ROOT / "includes" / "keycloak_guard.php"
        self.assertTrue(guard.exists(), "central Keycloak guard must exist")

        text = guard.read_text()
        self.assertIn("keycloak_login.php", text)
        self.assertIn("keycloak_callback.php", text)
        self.assertIn("logout.php", text)
        self.assertIn("newivr-admin", text)
        self.assertIn("newivr-agente", text)
        self.assertRegex(text, re.compile(r"profile_id['\"]?\]\s*=\s*1|return\s+1"))
        self.assertRegex(text, re.compile(r"profile_id['\"]?\]\s*=\s*6|return\s+6"))
        self.assertIn("preferred_username", text)
        self.assertIn("app_ivr_users", text)

    def test_login_backend_no_longer_accepts_password_login(self) -> None:
        backend = NEWIVR_ROOT / "login_backend.php"
        text = read_legacy_text(backend)

        self.assertNotIn("SELECT id, username, profile_id, status, password", text)
        self.assertNotIn("$password !== $user['password']", text)
        self.assertIn("Keycloak", text)
        self.assertIn("success", text)

    def test_login_page_starts_sso_instead_of_posting_passwords(self) -> None:
        login = NEWIVR_ROOT / "login.php"
        text = read_legacy_text(login)

        self.assertIn("keycloak_login.php", text)
        self.assertIn("require __DIR__ . '/keycloak_login.php'", text)
        self.assertNotIn("login_backend.php", text)
        self.assertNotIn("type=\"password\"", text)
        self.assertNotIn("name=\"password\"", text)

    def test_users_screen_is_backed_by_keycloak_synchronized_apis(self) -> None:
        users_root = NEWIVR_ROOT / "auth" / "users"
        index = read_legacy_text(users_root / "index.php")
        api_dir = users_root / "api"

        for filename in ["create_user.php", "update_user.php", "delete_user.php", "get_user.php"]:
            self.assertTrue((api_dir / filename).exists(), "missing users API: %s" % filename)

        self.assertIn("api/create_user.php", index)
        self.assertIn("api/update_user.php", index)
        self.assertIn("api/delete_user.php", index)
        self.assertIn("Keycloak", index)
        self.assertIn("openUserModal(<?php echo $user['id']; ?>)", index)

    def test_users_apis_sync_local_users_with_keycloak(self) -> None:
        users_root = NEWIVR_ROOT / "auth" / "users"
        helper = (users_root / "keycloak_users.php").read_text()
        create_api = (users_root / "api" / "create_user.php").read_text()
        update_api = (users_root / "api" / "update_user.php").read_text()
        delete_api = (users_root / "api" / "delete_user.php").read_text()

        self.assertIn("newivr_keycloak_admin_token", helper)
        self.assertIn("newivr_keycloak_user_role_for_profile", helper)
        self.assertIn("newivr-admin", helper)
        self.assertIn("newivr-agente", helper)
        self.assertIn("profile_id === 1", helper)
        self.assertIn("newivr_keycloak_create_user", create_api)
        self.assertIn("newivr_keycloak_update_user", update_api)
        self.assertIn("newivr_keycloak_delete_user", delete_api)

    def test_operations_documents_keycloak_runtime_contract(self) -> None:
        docs = (ROOT / "docs" / "operations.md").read_text()
        env_example = (ROOT / ".env.example").read_text()

        for expected in [
            "NEWIVR_KEYCLOAK_ISSUER",
            "NEWIVR_KEYCLOAK_CLIENT_ID",
            "NEWIVR_KEYCLOAK_CLIENT_SECRET",
            "newivr-admin",
            "newivr-agente",
            "preferred_username",
        ]:
            self.assertIn(expected, docs)

        for expected in [
            "NEWIVR_KEYCLOAK_ISSUER=",
            "NEWIVR_KEYCLOAK_CLIENT_ID=newivr",
            "NEWIVR_KEYCLOAK_ADMIN_ROLE=newivr-admin",
            "NEWIVR_KEYCLOAK_AGENT_ROLE=newivr-agente",
        ]:
            self.assertIn(expected, env_example)

    def test_logout_uses_id_token_hint_for_keycloak_logout(self) -> None:
        guard = (NEWIVR_ROOT / "includes" / "keycloak_guard.php").read_text()
        callback = (NEWIVR_ROOT / "keycloak_callback.php").read_text()
        logout = (NEWIVR_ROOT / "logout.php").read_text()

        self.assertIn("function newivr_establish_session($claims, $access_claims, $id_token)", guard)
        self.assertIn("$_SESSION['keycloak_id_token'] = $id_token;", guard)
        self.assertIn("newivr_establish_session($id_claims, $access_claims, $tokens['id_token'])", callback)
        self.assertIn("$id_token_hint = isset($_SESSION['keycloak_id_token'])", logout)
        self.assertIn("'id_token_hint' => $id_token_hint", logout)
        self.assertLess(logout.index("$id_token_hint"), logout.index("$_SESSION = array();"))
