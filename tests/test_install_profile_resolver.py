import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "resolve-install-profile.py"


def load_module():
    spec = importlib.util.spec_from_file_location("resolve_install_profile", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class InstallProfileResolverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()

    def test_discover_asterisk_packages_returns_sorted_versioned_packages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            repo_dir = repo_root / "Issabel"
            repo_dir.mkdir(parents=True)
            for name in [
                "asterisk18-18.6.0-2.el7.x86_64.rpm",
                "asterisk11-11.25.3-6.el7.x86_64.rpm",
                "asterisk16-addons-16.21.1-2.el7.x86_64.rpm",
                "asterisk13-13.38.3-1.el7.x86_64.rpm",
                "asterisk-11.25.3-0.el7.centos.x86_64.rpm",
            ]:
                (repo_dir / name).write_text("")

            discovered = self.module.discover_asterisk_packages(repo_root)

        self.assertEqual(
            [item.package_name for item in discovered],
            ["asterisk11", "asterisk13", "asterisk18"],
        )

    def test_available_modules_hide_callcenter_outside_asterisk_11(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            repo_dir = repo_root / "Issabel"
            repo_dir.mkdir(parents=True)
            for name in [
                "issabel-callcenter_4.0.0-5.noarch.rpm",
                "issabel-endpointconfig2_4.0.0-5.noarch.rpm",
                "issabel-reports-4.0.1-0.noarch.rpm",
            ]:
                (repo_dir / name).write_text("")

            ast11_modules = self.module.available_module_options(repo_root, "11")
            ast18_modules = self.module.available_module_options(repo_root, "18")

        self.assertIn("callcenter", ast11_modules)
        self.assertNotIn("callcenter", ast18_modules)
        self.assertIn("reports", ast18_modules)

    def test_default_selection_uses_standard_profile_and_filters_incompatible_modules(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            repo_dir = repo_root / "Issabel"
            repo_dir.mkdir(parents=True)
            for name in [
                "asterisk11-11.25.3-6.el7.x86_64.rpm",
                "asterisk18-18.6.0-2.el7.x86_64.rpm",
                "issabel-callcenter_4.0.0-5.noarch.rpm",
                "issabel-endpointconfig2_4.0.0-5.noarch.rpm",
                "issabel-reports-4.0.1-0.noarch.rpm",
            ]:
                (repo_dir / name).write_text("")

            selected = self.module.resolve_default_selection(
                repo_root=repo_root,
                preferred_asterisk_package=None,
                preferred_module_keys=["callcenter", "reports"],
            )

        self.assertEqual(selected.asterisk.package_name, "asterisk18")
        self.assertEqual(selected.optional_packages, ["issabel-reports"])


if __name__ == "__main__":
    unittest.main()
