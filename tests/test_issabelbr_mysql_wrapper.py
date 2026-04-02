import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WRAPPER_PATH = ROOT / "docker" / "issabel" / "rootfs" / "usr" / "local" / "bin" / "issabelbr-mysql-wrapper"


class IssabelBrMysqlWrapperTests(unittest.TestCase):
    def run_wrapper(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fake_mysql = tmp_path / "mysql-real"
            capture = tmp_path / "capture.txt"
            fake_mysql.write_text(
                "#!/bin/bash\n"
                "printf '%s\\n' \"$@\" > \"$WRAPPER_CAPTURE_PATH\"\n"
            )
            fake_mysql.chmod(0o755)

            env = os.environ.copy()
            env["ISSABELBR_REAL_MYSQL"] = str(fake_mysql)
            env["WRAPPER_CAPTURE_PATH"] = str(capture)

            result = subprocess.run(
                [str(WRAPPER_PATH), *args],
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            result.captured_args = capture.read_text().splitlines() if capture.exists() else []
            return result

    def test_strips_split_empty_password_argument(self) -> None:
        result = self.run_wrapper(["-uroot", "-p", "", "-e", "select 1"])

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.captured_args, ["-uroot", "-e", "select 1"])

    def test_strips_inline_empty_password_argument(self) -> None:
        result = self.run_wrapper(["-uroot", "-p", "", "--defaults-file=/tmp/my.cnf"])

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.captured_args, ["-uroot", "--defaults-file=/tmp/my.cnf"])

    def test_preserves_non_empty_password_argument(self) -> None:
        result = self.run_wrapper(["-uroot", "-psecret", "-e", "select 1"])

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.captured_args, ["-uroot", "-psecret", "-e", "select 1"])


if __name__ == "__main__":
    unittest.main()
