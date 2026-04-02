import json
import os
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
        self.assertEqual(service["build"]["args"]["ASTERISK_PACKAGE"], "asterisk18")
        self.assertEqual(service["build"]["args"]["OPTIONAL_PACKAGES"], "")
        self.assertEqual(service["environment"]["ISABEL_BOOTSTRAP_MARKER"], "/var/lib/issabel/.bootstrapped")
        self.assertEqual(service["environment"]["WORKSPACE_ROOT"], "/workspace")
        self.assertEqual(service["environment"]["ISSABEL_WEB_ADMIN_USER"], "admin")
        self.assertEqual(service["environment"]["ISSABEL_WEB_ADMIN_PASSWORD"], "DevAdmin123")
        self.assertEqual(service["hostname"], "issabel.local")
        self.assertIn("ISSABEL_WEB_ADMIN_USER: ${ISSABEL_WEB_ADMIN_USER:-admin}", compose_text)
        self.assertIn("ISSABEL_WEB_ADMIN_PASSWORD: ${ISSABEL_WEB_ADMIN_PASSWORD:-DevAdmin123}", compose_text)
        self.assertIn("ISSABEL_HTTP_PORT:-8088", compose_text)
        self.assertIn("ISSABEL_HTTPS_PORT:-8443", compose_text)
        self.assertIn("WORKSPACE_BIND_SOURCE:-.}", compose_text)
        self.assertIn("ASTERISK_PACKAGE: ${ISSABEL_INSTALL_ASTERISK_PACKAGE:-asterisk18}", compose_text)
        self.assertIn("OPTIONAL_PACKAGES: ${ISSABEL_INSTALL_OPTIONAL_PACKAGES:-}", compose_text)
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
        resolve_script = ROOT / "scripts" / "resolve-install-profile.py"
        sync_script = ROOT / "scripts" / "sync-workspace.sh"
        diagnose_script = ROOT / "scripts" / "diagnose.sh"
        build_script = ROOT / "scripts" / "build-image.sh"
        up_script = ROOT / "scripts" / "up.sh"
        bootstrap_script = ROOT / "docker" / "issabel" / "rootfs" / "usr" / "local" / "bin" / "bootstrap-issabel"
        firstboot_script = ROOT / "docker" / "issabel" / "rootfs" / "usr" / "local" / "bin" / "issabel-firstboot"
        install_profile_example = ROOT / ".issabel-install.conf.example"
        env_file = ROOT / ".env"
        env_example_file = ROOT / ".env.example"

        for path in [
            dockerfile,
            prepare_script,
            resolve_script,
            sync_script,
            diagnose_script,
            build_script,
            up_script,
            bootstrap_script,
            firstboot_script,
            install_profile_example,
            env_file,
            env_example_file,
        ]:
            self.assertTrue(path.exists(), f"{path} must exist")

        dockerfile_text = dockerfile.read_text()
        self.assertIn("FROM quay.io/centos/centos:7", dockerfile_text)
        self.assertIn("ARG ASTERISK_PACKAGE=asterisk18", dockerfile_text)
        self.assertIn("ARG OPTIONAL_PACKAGES=\"\"", dockerfile_text)
        self.assertIn("COPY .build/issabel-root /opt/issabel-root", dockerfile_text)
        self.assertIn("ENTRYPOINT [\"/usr/local/bin/bootstrap-issabel\"]", dockerfile_text)

        prepare_text = prepare_script.read_text()
        self.assertIn("issabel4-NIGHTLY-AST18-USB-DVD-x86_64-20211207.iso", prepare_text)
        self.assertIn("bsdtar -xf", prepare_text)
        self.assertIn(".build/issabel-root", prepare_text)

        resolve_text = resolve_script.read_text()
        self.assertIn("issabel-callcenter", resolve_text)
        self.assertIn("callcenter", resolve_text)
        self.assertIn("requires_major=\"11\"", resolve_text)

        build_text = build_script.read_text()
        self.assertIn("resolve-install-profile.py", build_text)
        self.assertIn(".build/install.env", build_text)

        up_text = up_script.read_text()
        self.assertIn("resolve-install-profile.py", up_text)
        self.assertIn(".build/install.env", up_text)

        sync_text = sync_script.read_text()
        self.assertIn("/workspace", sync_text)
        self.assertIn("/var/www/html/modules", sync_text)
        self.assertIn("rsync", sync_text)

        bootstrap_text = bootstrap_script.read_text()
        self.assertIn("ISABEL_BOOTSTRAP_MARKER", bootstrap_text)
        self.assertIn("mysql_install_db", bootstrap_text)
        self.assertIn("systemctl enable mariadb httpd", bootstrap_text)
        self.assertIn("/tftpboot", bootstrap_text)

        firstboot_text = firstboot_script.read_text()
        self.assertIn("CREATE DATABASE IF NOT EXISTS asterisk;", firstboot_text)
        self.assertIn("CREATE DATABASE IF NOT EXISTS call_center;", firstboot_text)
        self.assertIn("/usr/share/issabelpbx/tmp/issabelpbx-database-dump.sql", firstboot_text)
        self.assertIn("SHOW TABLES LIKE 'devices'", firstboot_text)
        self.assertIn("CALLCENTER_DB_USER", firstboot_text)
        self.assertIn("CALLCENTER_DB_PASSWORD", firstboot_text)
        self.assertIn("PBX_DB_USER", firstboot_text)
        self.assertIn("PBX_DB_PASSWORD", firstboot_text)
        self.assertIn("GRANT ALL PRIVILEGES ON call_center.* TO '${CALLCENTER_DB_USER}'@'localhost' IDENTIFIED BY '${CALLCENTER_DB_PASSWORD}';", firstboot_text)
        self.assertIn("GRANT ALL PRIVILEGES ON asterisk.* TO '${PBX_DB_USER}'@'localhost' IDENTIFIED BY '${PBX_DB_PASSWORD}';", firstboot_text)
        self.assertIn("/etc/issabelpbx.conf", firstboot_text)
        self.assertIn("/etc/issabel.conf", firstboot_text)
        self.assertIn("mysqlrootpwd", firstboot_text)
        self.assertIn("amiadminpwd", firstboot_text)
        self.assertIn("ISSABEL_MYSQL_ROOT_PASSWORD", firstboot_text)
        self.assertIn("/opt/issabel/dialer/dialerd.conf", firstboot_text)

        env_text = env_file.read_text()
        env_example_text = env_example_file.read_text()
        self.assertIn("ISSABEL_WEB_ADMIN_USER=admin", env_text)
        self.assertIn("ISSABEL_WEB_ADMIN_PASSWORD=DevAdmin123", env_text)
        self.assertIn("ISSABEL_HTTP_PORT=8088", env_text)
        self.assertIn("ISSABEL_HTTPS_PORT=8443", env_text)
        self.assertIn("ISSABEL_CONTAINER_NAME=issabel-dev", env_text)
        self.assertIn("ISSABEL_HOSTNAME=issabel.local", env_text)
        self.assertIn("WORKSPACE_BIND_SOURCE=.", env_text)
        self.assertIn("ISSABEL_WEB_ADMIN_USER=admin", env_example_text)
        self.assertIn("ISSABEL_WEB_ADMIN_PASSWORD=DevAdmin123", env_example_text)
        self.assertIn("ISSABEL_HTTP_PORT=8088", env_example_text)
        self.assertIn("ISSABEL_HTTPS_PORT=8443", env_example_text)
        self.assertIn("ISSABEL_CONTAINER_NAME=issabel-dev", env_example_text)
        self.assertIn("ISSABEL_HOSTNAME=issabel.local", env_example_text)
        self.assertIn("WORKSPACE_BIND_SOURCE=.", env_example_text)

    def test_compose_config_respects_runtime_env_overrides(self) -> None:
        compose_path = ROOT / "docker-compose.yml"
        env = os.environ.copy()
        env.update(
            {
                "ISSABEL_HTTP_PORT": "9080",
                "ISSABEL_HTTPS_PORT": "9443",
                "ISSABEL_CONTAINER_NAME": "issabel-custom",
                "ISSABEL_HOSTNAME": "pbx.local",
                "WORKSPACE_BIND_SOURCE": "/srv/workspace",
                "COMPOSE_PROJECT_NAME": "issabel-alt",
                "ISSABEL_INSTALL_ASTERISK_PACKAGE": "asterisk11",
                "ISSABEL_INSTALL_OPTIONAL_PACKAGES": "issabel-callcenter issabel-reports",
            }
        )

        proc = subprocess.run(
            ["docker", "compose", "-f", str(compose_path), "config", "--format", "json"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)

        config = json.loads(proc.stdout)
        service = config["services"]["issabel"]
        self.assertEqual(service["container_name"], "issabel-custom")
        self.assertEqual(service["hostname"], "pbx.local")
        self.assertEqual(service["build"]["args"]["ASTERISK_PACKAGE"], "asterisk11")
        self.assertEqual(service["build"]["args"]["OPTIONAL_PACKAGES"], "issabel-callcenter issabel-reports")
        self.assertEqual(service["ports"][0]["published"], "9080")
        self.assertEqual(service["ports"][1]["published"], "9443")
        self.assertEqual(service["volumes"][0]["source"], "/srv/workspace")

    def test_firstboot_seeds_callcenter_and_pbx_database_contract(self) -> None:
        firstboot_script = ROOT / "docker" / "issabel" / "rootfs" / "usr" / "local" / "bin" / "issabel-firstboot"
        firstboot_text = firstboot_script.read_text()

        self.assertIn("seed_pbx_schema", firstboot_text)
        self.assertIn("mysql_root asterisk <\"$pbx_dump\"", firstboot_text)
        self.assertIn("CREATE DATABASE IF NOT EXISTS call_center;", firstboot_text)
        self.assertIn("GRANT ALL PRIVILEGES ON call_center.* TO '${CALLCENTER_DB_USER}'@'localhost' IDENTIFIED BY '${CALLCENTER_DB_PASSWORD}';", firstboot_text)
        self.assertIn("ensure_config_value \"/opt/issabel/dialer/dialerd.conf\" \"dbuser\" \"$CALLCENTER_DB_USER\"", firstboot_text)
        self.assertIn("ensure_php_conf_value \"/etc/issabelpbx.conf\" \"AMPDBNAME\" \"asterisk\"", firstboot_text)


if __name__ == "__main__":
    unittest.main()
