import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class NewIvrKeycloakSyncTests(unittest.TestCase):
    def test_sync_workspace_runs_overlay_apply_hooks(self) -> None:
        sync_script = ROOT / "docker" / "issabel" / "rootfs" / "usr" / "local" / "bin" / "sync-workspace"
        text = sync_script.read_text()

        self.assertIn("overlay-apply", text)
        self.assertIn("OVERLAY_ROOT", text)
        self.assertIn("hooks/apply.sh", text)

    def test_newivr_overlay_hook_provisions_embedded_keycloak(self) -> None:
        hook = ROOT / "overlays" / "NewIvr" / "hooks" / "apply.sh"
        self.assertTrue(hook.exists())
        text = hook.read_text()

        self.assertIn("KEYCLOAK_VERSION", text)
        self.assertIn("JRE_URL", text)
        self.assertIn("/opt/newivr/keycloak", text)
        self.assertIn("/etc/newivr/keycloak.env", text)
        self.assertIn("127.0.0.1", text)
        self.assertIn("18080", text)
        self.assertIn("app_ivr_users", text)
        self.assertIn("post.logout.redirect.uris", text)
        self.assertIn("configure_keycloak_client", text)
        self.assertNotIn("docker run", text)
        self.assertNotIn("docker compose", text)

    def test_realm_import_defines_client_roles_and_homologation_users(self) -> None:
        realm_path = ROOT / "overlays" / "NewIvr" / "keycloak" / "newivr-realm.json"
        self.assertTrue(realm_path.exists())
        realm = json.loads(realm_path.read_text())

        self.assertEqual(realm["realm"], "newivr")
        role_names = {role["name"] for role in realm["roles"]["realm"]}
        self.assertIn("newivr-admin", role_names)
        self.assertIn("newivr-agente", role_names)

        client = next((item for item in realm["clients"] if item["clientId"] == "newivr"), None)
        self.assertIsNotNone(client)
        self.assertEqual(client["secret"], "newivr-hml-secret")
        self.assertIn("https://127.0.0.1:8443/NewIvr/keycloak_callback.php", client["redirectUris"])
        self.assertIn("post.logout.redirect.uris", client["attributes"])
        self.assertIn("https://127.0.0.1:8443/NewIvr/login.php", client["attributes"]["post.logout.redirect.uris"])

        users = {user["username"]: user for user in realm["users"]}
        self.assertIn("admin", users)
        self.assertIn("agente", users)
        self.assertIn("newivr-admin", users["admin"]["realmRoles"])
        self.assertIn("newivr-agente", users["agente"]["realmRoles"])

    def test_env_points_newivr_to_sync_managed_keycloak(self) -> None:
        env_text = (ROOT / ".env").read_text()
        self.assertIn("NEWIVR_KEYCLOAK_ISSUER=http://127.0.0.1:18080/realms/newivr", env_text)
        self.assertIn("NEWIVR_KEYCLOAK_CLIENT_SECRET=newivr-hml-secret", env_text)
        self.assertIn("NEWIVR_KEYCLOAK_REDIRECT_URI=https://127.0.0.1:8443/NewIvr/keycloak_callback.php", env_text)
        self.assertIn("NEWIVR_KEYCLOAK_POST_LOGOUT_REDIRECT_URIS=https://127.0.0.1:8443/NewIvr/login.php", env_text)
