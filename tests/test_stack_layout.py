import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class IssabelStackLayoutTests(unittest.TestCase):
    def run_sync_workspace(self, workspace_root: Path, web_root: Path, modules_target: Path, state_root: Path) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.update(
            {
                "WORKSPACE_ROOT": str(workspace_root),
                "ISSABEL_WEB_ROOT": str(web_root),
                "ISSABEL_MODULES_TARGET_ROOT": str(modules_target),
                "ISSABEL_MODULE_STATE_ROOT": str(state_root),
                "ISSABEL_INTEGRATIONS_TARGET_ROOT": str(workspace_root / "published-integrations"),
            }
        )
        return subprocess.run(
            [str(ROOT / "docker" / "issabel" / "rootfs" / "usr" / "local" / "bin" / "sync-workspace")],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
        )

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
        self.assertEqual(service["build"]["args"]["ASTERISK_PACKAGE"], "asterisk11")
        self.assertEqual(
            service["build"]["args"]["OPTIONAL_PACKAGES"],
            "issabel-agenda issabel-callcenter issabel-endpointconfig2 issabel-extras issabel-reports",
        )
        self.assertEqual(service["environment"]["ISABEL_BOOTSTRAP_MARKER"], "/var/lib/issabel/.bootstrapped")
        self.assertEqual(service["environment"]["WORKSPACE_ROOT"], "/workspace")
        self.assertEqual(service["environment"]["ISSABEL_WEB_ADMIN_USER"], "admin")
        self.assertEqual(service["environment"]["ISSABEL_WEB_ADMIN_PASSWORD"], "DevAdmin123")
        self.assertEqual(service["environment"]["ISSABEL_HTTPS_PORT"], "8443")
        self.assertEqual(service["hostname"], "issabel.local")
        self.assertIn("ISSABEL_WEB_ADMIN_USER: ${ISSABEL_WEB_ADMIN_USER:-admin}", compose_text)
        self.assertIn("ISSABEL_WEB_ADMIN_PASSWORD: ${ISSABEL_WEB_ADMIN_PASSWORD:-DevAdmin123}", compose_text)
        self.assertIn("ISSABEL_HTTPS_PORT: ${ISSABEL_HTTPS_PORT:-8443}", compose_text)
        self.assertIn("ISSABEL_SIP_PORT: ${ISSABEL_SIP_PORT:-5060}", compose_text)
        self.assertIn("ISSABEL_RTP_START: ${ISSABEL_RTP_START:-10000}", compose_text)
        self.assertIn("ISSABEL_RTP_END: ${ISSABEL_RTP_END:-10100}", compose_text)
        self.assertIn("ISSABEL_HTTP_PORT:-8088", compose_text)
        self.assertIn("ISSABEL_HTTPS_PORT:-8443", compose_text)
        self.assertIn("ISSABEL_SIP_PORT:-5060", compose_text)
        self.assertIn("ISSABEL_RTP_START:-10000", compose_text)
        self.assertIn("ISSABEL_RTP_END:-10100", compose_text)
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
        self.assertEqual(service["ports"][2]["published"], "5060")
        self.assertEqual(service["ports"][2]["target"], 5060)
        self.assertEqual(service["ports"][2]["protocol"], "udp")
        self.assertEqual(service["ports"][3]["published"], "10000")
        self.assertEqual(service["ports"][3]["target"], 10000)
        self.assertEqual(service["ports"][3]["protocol"], "udp")
        self.assertEqual(service["ports"][-1]["published"], "10100")
        self.assertEqual(service["ports"][-1]["target"], 10100)
        self.assertEqual(service["ports"][-1]["protocol"], "udp")
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
        rootfs_sync_script = ROOT / "docker" / "issabel" / "rootfs" / "usr" / "local" / "bin" / "sync-workspace"
        diagnose_script = ROOT / "scripts" / "diagnose.sh"
        build_script = ROOT / "scripts" / "build-image.sh"
        up_script = ROOT / "scripts" / "up.sh"
        helper_wrapper = ROOT / "docker" / "issabel" / "rootfs" / "usr" / "bin" / "issabel-helper"
        bootstrap_script = ROOT / "docker" / "issabel" / "rootfs" / "usr" / "local" / "bin" / "bootstrap-issabel"
        firstboot_script = ROOT / "docker" / "issabel" / "rootfs" / "usr" / "local" / "bin" / "issabel-firstboot"
        post_restore_script = ROOT / "docker" / "issabel" / "rootfs" / "usr" / "local" / "bin" / "apply-issabelbr-post-restore"
        install_profile_example = ROOT / ".issabel-install.conf.example"
        env_file = ROOT / ".env"
        env_example_file = ROOT / ".env.example"
        modules_dir = ROOT / "modules"
        modules_readme = modules_dir / "README.md"
        overlays_dir = ROOT / "overlays"
        overlays_readme = overlays_dir / "README.md"

        for path in [
            dockerfile,
            prepare_script,
            resolve_script,
            sync_script,
            rootfs_sync_script,
            diagnose_script,
            build_script,
            up_script,
            helper_wrapper,
            bootstrap_script,
            firstboot_script,
            post_restore_script,
            install_profile_example,
            env_file,
            env_example_file,
            modules_dir,
            modules_readme,
            overlays_dir,
            overlays_readme,
        ]:
            self.assertTrue(path.exists(), f"{path} must exist")

        dockerfile_text = dockerfile.read_text()
        self.assertIn("FROM quay.io/centos/centos:7", dockerfile_text)
        self.assertIn("ARG ASTERISK_PACKAGE=asterisk18", dockerfile_text)
        self.assertIn("ARG OPTIONAL_PACKAGES=\"\"", dockerfile_text)
        self.assertIn("ARG INSTALL_ISSABELBR_POST_PATCH=1", dockerfile_text)
        self.assertIn("COPY .build/issabel-root /opt/issabel-root", dockerfile_text)
        self.assertIn("/usr/local/bin/apply-issabelbr-build-assets", dockerfile_text)
        self.assertIn("/usr/local/bin/apply-issabelbr-post-restore", dockerfile_text)
        self.assertIn("/usr/bin/issabel-helper", dockerfile_text)
        self.assertIn("ENTRYPOINT [\"/usr/local/bin/bootstrap-issabel\"]", dockerfile_text)

        helper_wrapper_text = helper_wrapper.read_text()
        self.assertIn('if [ "$1" = "backupengine" ]; then', helper_wrapper_text)
        self.assertIn('if [ "$arg" = "--restore" ]; then', helper_wrapper_text)
        self.assertIn('/usr/local/bin/apply-issabelbr-post-restore', helper_wrapper_text)

        post_restore_text = post_restore_script.read_text()
        self.assertIn('ISSABELBR_RUNTIME_ASSETS_DIR', post_restore_text)
        self.assertIn('ISSABEL_INSTALL_ASTERISK_PACKAGE', post_restore_text)
        self.assertIn('rpm -q asterisk11', post_restore_text)
        self.assertIn('apply_static_assets', post_restore_text)
        self.assertIn('apply_file_reconciliations', post_restore_text)
        self.assertIn('/usr/local/bin/issabel-firstboot', post_restore_text)
        self.assertIn('/usr/sbin/amportal reload', post_restore_text)

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
        self.assertIn("/usr/local/bin/sync-workspace", sync_text)

        rootfs_sync_text = rootfs_sync_script.read_text()
        self.assertIn("STATE_ROOT", rootfs_sync_text)
        self.assertIn("apply_module_migrations", rootfs_sync_text)
        self.assertIn("revert_removed_modules", rootfs_sync_text)
        self.assertIn("/var/lib/asterisk/issabel-module-state", rootfs_sync_text)
        self.assertIn("ISSABEL_WEB_ROOT", rootfs_sync_text)
        self.assertIn("verify_overlay_conflicts", rootfs_sync_text)
        self.assertIn("apply_overlay", rootfs_sync_text)
        self.assertIn("restore_overlay", rootfs_sync_text)
        self.assertIn("OVERLAYS_SOURCE_ROOT", rootfs_sync_text)
        self.assertIn("rsync", sync_text)

        bootstrap_text = bootstrap_script.read_text()
        self.assertIn("ISABEL_BOOTSTRAP_MARKER", bootstrap_text)
        self.assertIn("mysql_install_db", bootstrap_text)
        self.assertIn("systemctl enable mariadb httpd", bootstrap_text)
        self.assertIn("reuse_running_service", bootstrap_text)
        self.assertIn('reuse_running_service httpd', bootstrap_text)
        self.assertIn('reuse_running_service asterisk', bootstrap_text)
        self.assertIn("/tftpboot", bootstrap_text)
        self.assertIn("start_callcenter", bootstrap_text)
        self.assertIn("issabeldialer", bootstrap_text)
        self.assertIn('exec > >(tee -a "$BOOTSTRAP_LOG") 2>&1', bootstrap_text)
        self.assertIn("  /usr/local/bin/issabel-firstboot\n", bootstrap_text)
        self.assertNotIn("/usr/local/bin/issabel-firstboot || true", bootstrap_text)

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
        self.assertIn("find_callcenter_schema", firstboot_text)
        self.assertIn("seed_callcenter_schema", firstboot_text)
        self.assertIn("SHOW TABLES LIKE 'agent'", firstboot_text)
        self.assertIn("firstboot_call_center.sql", firstboot_text)
        self.assertIn("ISSABEL_MYSQL_ROOT_PASSWORD", firstboot_text)
        self.assertIn("/opt/issabel/dialer/dialerd.conf", firstboot_text)
        self.assertIn("reconcile_http_redirect_port", firstboot_text)
        self.assertIn("reconcile_manager_secret", firstboot_text)
        self.assertIn("reconcile_manager_general_settings", firstboot_text)
        self.assertIn("enabled = yes", firstboot_text)
        self.assertIn("reconcile_sip_bridge_settings", firstboot_text)
        self.assertIn("ISSABEL_SIP_BIND_ADDRESS", firstboot_text)
        self.assertIn("ISSABEL_SIP_EXTERNAL_ADDRESS", firstboot_text)
        self.assertIn("ISSABEL_RTP_START", firstboot_text)
        self.assertIn("ISSABEL_RTP_END", firstboot_text)
        self.assertIn("/etc/asterisk/sip_general_custom.conf", firstboot_text)
        self.assertIn("/etc/asterisk/rtp_custom.conf", firstboot_text)
        self.assertIn("/etc/httpd/conf.d/issabel.conf", firstboot_text)
        self.assertIn("/etc/asterisk/manager.conf", firstboot_text)
        self.assertIn("channelvars = DIALERID,DIALERVAR", firstboot_text)
        self.assertIn('local read_permissions="system,call,log,verbose,command,agent,user,config,command,dtmf,reporting,cdr,dialplan,originate"', firstboot_text)
        self.assertIn('local write_permissions="system,call,log,verbose,command,agent,user,config,command,dtmf,reporting,cdr,dialplan,originate"', firstboot_text)
        self.assertIn('python - "$file_path" "$HTTPS_REDIRECT_PORT"', firstboot_text)
        self.assertIn('RewriteCond %%{HTTP_HOST} ^([^:]+)(?::\\\\d+)?$', firstboot_text)
        self.assertIn('https://%%1:%s%%{REQUEST_URI}', firstboot_text)
        self.assertNotIn("yum ", firstboot_text)
        self.assertNotIn("wget ", firstboot_text)
        self.assertNotIn("apply_issabelbr_post_patch", firstboot_text)
        self.assertNotIn("configure_el7_repositories", firstboot_text)

        build_assets_text = (ROOT / "docker" / "issabel" / "rootfs" / "usr" / "local" / "bin" / "apply-issabelbr-build-assets").read_text()
        self.assertIn("ISSABELBR_RUNTIME_ASSETS_DIR", build_assets_text)
        self.assertIn("ISSABEL_INSTALL_ASTERISK_PACKAGE", build_assets_text)
        self.assertIn("rpm -q asterisk11", build_assets_text)
        self.assertIn("cache_runtime_assets", build_assets_text)
        self.assertIn("/opt/issabelbr-runtime-assets", build_assets_text)

        env_text = env_file.read_text()
        env_example_text = env_example_file.read_text()
        self.assertIn("ISSABEL_WEB_ADMIN_USER=admin", env_text)
        self.assertIn("ISSABEL_WEB_ADMIN_PASSWORD=DevAdmin123", env_text)
        self.assertIn("ISSABEL_HTTP_PORT=8088", env_text)
        self.assertIn("ISSABEL_HTTPS_PORT=8443", env_text)
        self.assertIn("ISSABEL_CONTAINER_NAME=issabel-dev", env_text)
        self.assertIn("ISSABEL_HOSTNAME=issabel.local", env_text)
        self.assertIn("WORKSPACE_BIND_SOURCE=.", env_text)
        self.assertIn("ISSABEL_INSTALL_ASTERISK_PACKAGE=asterisk11", env_text)
        self.assertIn(
            "ISSABEL_INSTALL_OPTIONAL_PACKAGES='issabel-agenda issabel-callcenter issabel-endpointconfig2 issabel-extras issabel-reports'",
            env_text,
        )
        self.assertIn("ISSABEL_INSTALL_MODULE_PROFILE=full", env_text)
        self.assertIn("ISSABEL_INSTALL_ISSABELBR_POST_PATCH=1", env_text)
        self.assertIn("ISSABEL_WEB_ADMIN_USER=admin", env_example_text)
        self.assertIn("ISSABEL_WEB_ADMIN_PASSWORD=DevAdmin123", env_example_text)
        self.assertIn("ISSABEL_HTTP_PORT=8088", env_example_text)
        self.assertIn("ISSABEL_HTTPS_PORT=8443", env_example_text)
        self.assertIn("ISSABEL_CONTAINER_NAME=issabel-dev", env_example_text)
        self.assertIn("ISSABEL_HOSTNAME=issabel.local", env_example_text)
        self.assertIn("WORKSPACE_BIND_SOURCE=.", env_example_text)

        modules_readme_text = modules_readme.read_text()
        self.assertIn("web/", modules_readme_text)
        self.assertIn("migrations/apply", modules_readme_text)
        self.assertIn("migrations/revert", modules_readme_text)
        self.assertIn("hooks/apply.sh", modules_readme_text)
        self.assertIn("./scripts/sync-workspace.sh", modules_readme_text)
        self.assertIn("overlays/", modules_readme_text)

        overlays_readme_text = overlays_readme.read_text()
        self.assertIn("web_root/", overlays_readme_text)
        self.assertIn("/var/www/html", overlays_readme_text)
        self.assertIn("conflicting overlays", overlays_readme_text)

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
        self.assertEqual(service["build"]["args"]["INSTALL_ISSABELBR_POST_PATCH"], "1")
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
        self.assertIn("reconcile_ami_credentials", firstboot_text)
        self.assertIn("reconcile_manager_secret", firstboot_text)
        self.assertIn("local read_permissions=", firstboot_text)
        self.assertIn("local write_permissions=", firstboot_text)
        self.assertIn("normalize_agents_conf", firstboot_text)
        self.assertIn("/etc/asterisk/agents.conf", firstboot_text)
        self.assertIn("INSERT INTO call_center.valor_config (config_key, config_value)", firstboot_text)
        self.assertIn("'asterisk.astuser'", firstboot_text)
        self.assertIn("'asterisk.astpass'", firstboot_text)
        self.assertNotIn("/usr/local/bin/sync-workspace --once", firstboot_text)
        self.assertNotIn("ensure_runtime_services", firstboot_text)
        self.assertNotIn("apply_issabelbr_post_patch", firstboot_text)

    def test_build_time_issabelbr_helper_carries_runtime_heavy_work(self) -> None:
        helper_script = ROOT / "docker" / "issabel" / "rootfs" / "usr" / "local" / "bin" / "apply-issabelbr-build-assets"
        helper_text = helper_script.read_text()

        self.assertIn("INSTALL_ISSABELBR_POST_PATCH", helper_text)
        self.assertIn("configure_el7_repositories", helper_text)
        self.assertIn("git clone https://github.com/ibinetwork/IssabelBR.git", helper_text)
        self.assertIn("yum install", helper_text)
        self.assertIn("asterisk-codec-g729", helper_text)
        self.assertIn("sngrep", helper_text)
        self.assertIn('${ISSABELBR_REPO_DIR}/web/', helper_text)
        self.assertIn('${ISSABELBR_REPO_DIR}/audio/', helper_text)
        self.assertIn('${ISSABELBR_REPO_DIR}/etc/asterisk/', helper_text)
        self.assertIn('${ISSABELBR_REPO_DIR}/web2/', helper_text)

    def test_gitignore_and_docs_cover_local_module_contract(self) -> None:
        gitignore_text = (ROOT / ".gitignore").read_text()
        self.assertIn("modules/", gitignore_text)
        self.assertIn("overlays/", gitignore_text)

        operations_text = (ROOT / "docs" / "operations.md").read_text()
        self.assertIn("module contract", operations_text)
        self.assertIn("overlays/<overlay>/web_root", operations_text)
        self.assertIn("migrations/apply/<database>", operations_text)
        self.assertIn("migrations/revert/<database>", operations_text)
        self.assertIn("hooks/apply.sh", operations_text)
        self.assertIn("hooks/revert.sh", operations_text)
        self.assertIn("URL direta", operations_text)

    def test_sync_workspace_applies_and_reverts_web_root_overlay(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            workspace_root = tmp_root / "workspace"
            web_root = tmp_root / "web-root"
            modules_target = tmp_root / "published-modules"
            state_root = tmp_root / "state"
            module_root = workspace_root / "modules" / "standalone-a"
            overlay_root = workspace_root / "overlays" / "theme-a" / "web_root"
            web_payload_root = module_root / "web"

            (workspace_root / "modules").mkdir(parents=True)
            (workspace_root / "overlays").mkdir(parents=True)
            web_root.mkdir(parents=True)
            overlay_root.mkdir(parents=True)
            web_payload_root.mkdir(parents=True)
            (web_root / "index.php").write_text("core-index\n")
            (web_root / "themes").mkdir()
            (overlay_root / "index.php").write_text("theme-index\n")
            (overlay_root / "themes" / "custom.css").parent.mkdir(parents=True)
            (overlay_root / "themes" / "custom.css").write_text("body { color: red; }\n")
            (web_payload_root / "info.txt").write_text("payload\n")

            first_run = self.run_sync_workspace(workspace_root, web_root, modules_target, state_root)
            self.assertEqual(first_run.returncode, 0, first_run.stderr)
            self.assertEqual((web_root / "index.php").read_text(), "theme-index\n")
            self.assertEqual((web_root / "themes" / "custom.css").read_text(), "body { color: red; }\n")
            self.assertEqual((modules_target / "standalone-a" / "info.txt").read_text(), "payload\n")

            overlay_state = state_root / "overlays" / "theme-a"
            self.assertTrue((overlay_state / "runtime" / "web-root-overlay-state.txt").exists())
            self.assertTrue((overlay_state / "snapshot" / "original-web-root" / "index.php").exists())

            (workspace_root / "overlays" / "theme-a").rename(tmp_root / "theme-a-removed")
            second_run = self.run_sync_workspace(workspace_root, web_root, modules_target, state_root)
            self.assertEqual(second_run.returncode, 0, second_run.stderr)
            self.assertEqual((web_root / "index.php").read_text(), "core-index\n")
            self.assertFalse((web_root / "themes" / "custom.css").exists())
            self.assertFalse((state_root / "overlays" / "theme-a").exists())

    def test_sync_workspace_blocks_conflicting_web_root_overlays(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            workspace_root = tmp_root / "workspace"
            web_root = tmp_root / "web-root"
            modules_target = tmp_root / "published-modules"
            state_root = tmp_root / "state"

            for overlay_name, content in [("theme-a", "a\n"), ("theme-b", "b\n")]:
                overlay_root = workspace_root / "overlays" / overlay_name / "web_root"
                overlay_root.mkdir(parents=True, exist_ok=True)
                (overlay_root / "index.php").write_text(content)

            web_root.mkdir(parents=True)
            (web_root / "index.php").write_text("core\n")

            result = self.run_sync_workspace(workspace_root, web_root, modules_target, state_root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("conflict", result.stderr.lower())
            self.assertEqual((web_root / "index.php").read_text(), "core\n")


if __name__ == "__main__":
    unittest.main()
