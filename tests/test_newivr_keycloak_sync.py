import subprocess
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

    def test_newivr_overlay_sources_are_standalone_and_not_tracked_here(self) -> None:
        proc = subprocess.run(
            ["git", "ls-files", "overlays/NewIvr"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "")

        gitignore_text = (ROOT / ".gitignore").read_text()
        overlays_readme = (ROOT / "overlays" / "README.md").read_text()
        self.assertIn("overlays/*", gitignore_text)
        self.assertIn("Everything inside this directory is ignored by Git", overlays_readme)

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

    def test_env_points_newivr_to_sync_managed_keycloak(self) -> None:
        env_text = (ROOT / ".env.example").read_text()
        self.assertIn("NEWIVR_KEYCLOAK_ISSUER=http://127.0.0.1:18080/realms/newivr", env_text)
        self.assertIn("NEWIVR_KEYCLOAK_HTTP_BIND_HOST=", env_text)
        self.assertIn("NEWIVR_KEYCLOAK_CLIENT_SECRET=", env_text)
        self.assertIn("NEWIVR_KEYCLOAK_REDIRECT_URI=https://127.0.0.1:8443/NewIvr/keycloak_callback.php", env_text)
        self.assertIn("NEWIVR_KEYCLOAK_POST_LOGOUT_REDIRECT_URIS=https://127.0.0.1:8443/NewIvr/login.php", env_text)
