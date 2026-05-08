import json
import re
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
        self.assertIn("KEYCLOAK_HTTP_BIND_HOST", text)
        self.assertIn("18080", text)
        self.assertIn("app_ivr_profiles", text)
        self.assertIn("Administrador", text)
        self.assertIn("Agente", text)
        self.assertIn("permissions TEXT NULL", text)
        self.assertRegex(text, re.compile(r"\(1,'Administrador'.*?\)", re.DOTALL))
        self.assertRegex(text, re.compile(r"\(6,'Agente'.*?\)", re.DOTALL))
        self.assertIn("profile_id=VALUES(profile_id)", text)
        self.assertIn("app_ivr_users", text)
        self.assertLess(text.rindex("ensure_local_users"), text.rindex("require_keycloak_config"))
        self.assertIn("post.logout.redirect.uris", text)
        self.assertIn("configure_keycloak_client", text)
        self.assertIn("newivr-keycloak start", text)
        self.assertNotIn("docker run", text)
        self.assertNotIn("docker compose", text)

    def test_bootstrap_restarts_sync_managed_keycloak_after_container_restart(self) -> None:
        runner = ROOT / "docker" / "issabel" / "rootfs" / "usr" / "local" / "bin" / "newivr-keycloak"
        bootstrap = ROOT / "docker" / "issabel" / "rootfs" / "usr" / "local" / "bin" / "bootstrap-issabel"
        dockerfile = ROOT / "docker" / "issabel" / "Dockerfile"

        self.assertTrue(runner.exists())
        runner_text = runner.read_text()
        bootstrap_text = bootstrap.read_text()
        dockerfile_text = dockerfile.read_text()

        self.assertIn("/etc/newivr/keycloak.env", runner_text)
        self.assertIn("/opt/newivr/keycloak", runner_text)
        self.assertIn("start-dev", runner_text)
        self.assertIn("NEWIVR_KEYCLOAK_INTERNAL_BASE_URL", runner_text)
        self.assertIn("NEWIVR_KEYCLOAK_HOSTNAME", runner_text)
        self.assertIn("NEWIVR_KEYCLOAK_PROXY_HEADERS", runner_text)
        self.assertIn("keycloak_process_matches_config", runner_text)
        self.assertIn('keycloak_args+=(--hostname="$KEYCLOAK_HOSTNAME")', runner_text)
        self.assertIn('keycloak_args+=(--proxy-headers="$KEYCLOAK_PROXY_HEADERS")', runner_text)
        self.assertIn("newivr-keycloak start", bootstrap_text)
        self.assertIn("newivr-keycloak", dockerfile_text)

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
        self.assertNotIn("secret", client, "client secret must be injected from env by the hook")
        self.assertFalse(client["directAccessGrantsEnabled"])
        self.assertIn("https://127.0.0.1:8443/NewIvr/keycloak_callback.php", client["redirectUris"])
        self.assertIn("post.logout.redirect.uris", client["attributes"])
        self.assertIn("https://127.0.0.1:8443/NewIvr/login.php", client["attributes"]["post.logout.redirect.uris"])

        self.assertNotIn("users", realm, "realm import must not ship default user passwords")

    def test_env_points_newivr_to_sync_managed_keycloak(self) -> None:
        env_text = (ROOT / ".env").read_text()
        self.assertIn("NEWIVR_KEYCLOAK_ISSUER=http://127.0.0.1:18080/realms/newivr", env_text)
        self.assertIn("NEWIVR_KEYCLOAK_HTTP_BIND_HOST=", env_text)
        self.assertIn("NEWIVR_KEYCLOAK_CLIENT_SECRET=", env_text)
        self.assertIn("NEWIVR_KEYCLOAK_REDIRECT_URI=https://127.0.0.1:8443/NewIvr/keycloak_callback.php", env_text)
        self.assertIn("NEWIVR_KEYCLOAK_POST_LOGOUT_REDIRECT_URIS=https://127.0.0.1:8443/NewIvr/login.php", env_text)
