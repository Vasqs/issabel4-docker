import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "docker" / "issabel" / "rootfs" / "usr" / "local" / "bin" / "configure-el7-repositories"


class ConfigureEl7RepositoriesTests(unittest.TestCase):
    def test_replaces_centos_base_repo_with_almalinux_el7_mirror(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            yum_repos = root / "etc" / "yum.repos.d"
            yum_repos.mkdir(parents=True)
            (yum_repos / "CentOS-Base.repo").write_text("[base]\nmirrorlist=http://mirror.centos.org/\n")

            env = os.environ.copy()
            env["ISSABEL_REPO_ROOT"] = str(root)

            result = subprocess.run(
                [str(SCRIPT_PATH)],
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0)
            self.assertIn("https://el7.repo.almalinux.org/centos/CentOS-Base.repo", result.stdout)
            repo_text = (yum_repos / "CentOS-Base.repo").read_text()
            self.assertIn("el7.repo.almalinux.org/centos", repo_text)


if __name__ == "__main__":
    unittest.main()
