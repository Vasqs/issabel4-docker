import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class IssabelStackLayoutTests(unittest.TestCase):
    def test_compose_declares_expected_runtime_contract(self) -> None:
        compose_path = ROOT / "docker-compose.yml"
        self.assertTrue(compose_path.exists(), "docker-compose.yml must exist")
        compose_text = compose_path.read_text()

        proc = subprocess.run(
            ["docker", "compose", "-f", str(compose_path), "config", "--format", "json"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)

        config = json.loads(proc.stdout)
        self.assertIn("services", config)
        self.assertIn("issabel", config["services"])

        service = config["services"]["issabel"]
        self.assertTrue(service["privileged"])
        self.assertEqual(service["container_name"], "issabel-dev")
        self.assertEqual(service["restart"], "unless-stopped")
        self.assertEqual(service["build"]["dockerfile"], "docker/issabel/Dockerfile")
        self.assertEqual(service["environment"]["ISABEL_BOOTSTRAP_MARKER"], "/var/lib/issabel/.bootstrapped")
        self.assertEqual(service["environment"]["WORKSPACE_ROOT"], "/workspace")
        self.assertEqual(service["environment"]["ISSABEL_WEB_ADMIN_USER"], "admin")
        self.assertEqual(service["environment"]["ISSABEL_WEB_ADMIN_PASSWORD"], "DevAdmin123")
        self.assertIn("ISSABEL_WEB_ADMIN_USER: ${ISSABEL_WEB_ADMIN_USER:-admin}", compose_text)
        self.assertIn("ISSABEL_WEB_ADMIN_PASSWORD: ${ISSABEL_WEB_ADMIN_PASSWORD:-DevAdmin123}", compose_text)
        self.assertIn("/workspace", service["volumes"][0]["target"])
        self.assertIn("/sys/fs/cgroup", service["volumes"][1]["target"])
        self.assertEqual(service["healthcheck"]["test"][0], "CMD-SHELL")
        self.assertIn("curl -fsS http://127.0.0.1/", service["healthcheck"]["test"][1])
        self.assertEqual(service["ports"][0]["published"], "8088")
        self.assertEqual(service["ports"][0]["target"], 80)
        self.assertEqual(service["ports"][1]["published"], "8443")
        self.assertEqual(service["ports"][1]["target"], 443)
        self.assertEqual(service["tmpfs"], ["/run", "/run/lock", "/tmp"])

        volumes = config["volumes"]
        for volume_name in [
            "issabel-etc",
            "issabel-var-lib",
            "issabel-var-log",
            "issabel-mysql",
            "issabel-spool",
        ]:
            self.assertIn(volume_name, volumes)

    def test_dockerfile_and_scripts_exist_with_expected_contract(self) -> None:
        dockerfile = ROOT / "docker" / "issabel" / "Dockerfile"
        prepare_script = ROOT / "scripts" / "prepare-iso-root.sh"
        sync_script = ROOT / "scripts" / "sync-workspace.sh"
        diagnose_script = ROOT / "scripts" / "diagnose.sh"
        bootstrap_script = ROOT / "docker" / "issabel" / "rootfs" / "usr" / "local" / "bin" / "bootstrap-issabel"
        env_file = ROOT / ".env"
        env_example_file = ROOT / ".env.example"

        for path in [dockerfile, prepare_script, sync_script, diagnose_script, bootstrap_script, env_file, env_example_file]:
            self.assertTrue(path.exists(), f"{path} must exist")

        dockerfile_text = dockerfile.read_text()
        self.assertIn("FROM quay.io/centos/centos:7", dockerfile_text)
        self.assertIn("COPY .build/issabel-root /opt/issabel-root", dockerfile_text)
        self.assertIn("ENTRYPOINT [\"/usr/local/bin/bootstrap-issabel\"]", dockerfile_text)

        prepare_text = prepare_script.read_text()
        self.assertIn("issabel4-NIGHTLY-AST18-USB-DVD-x86_64-20211207.iso", prepare_text)
        self.assertIn("bsdtar -xf", prepare_text)
        self.assertIn(".build/issabel-root", prepare_text)

        sync_text = sync_script.read_text()
        self.assertIn("/workspace", sync_text)
        self.assertIn("/var/www/html/modules", sync_text)
        self.assertIn("rsync", sync_text)

        bootstrap_text = bootstrap_script.read_text()
        self.assertIn("ISABEL_BOOTSTRAP_MARKER", bootstrap_text)
        self.assertIn("mysql_install_db", bootstrap_text)
        self.assertIn("systemctl enable mariadb httpd", bootstrap_text)

        env_text = env_file.read_text()
        env_example_text = env_example_file.read_text()
        self.assertIn("ISSABEL_WEB_ADMIN_USER=admin", env_text)
        self.assertIn("ISSABEL_WEB_ADMIN_PASSWORD=DevAdmin123", env_text)
        self.assertIn("ISSABEL_WEB_ADMIN_USER=admin", env_example_text)
        self.assertIn("ISSABEL_WEB_ADMIN_PASSWORD=DevAdmin123", env_example_text)


if __name__ == "__main__":
    unittest.main()
