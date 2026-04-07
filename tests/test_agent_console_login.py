import os
import re
import unittest

import requests
import urllib3


BASE_URL = os.environ.get("ISSABEL_BASE_URL", "https://127.0.0.1:8443")
WEB_ADMIN_USER = os.environ.get("ISSABEL_WEB_ADMIN_USER", "admin")
WEB_ADMIN_PASSWORD = os.environ.get("ISSABEL_WEB_ADMIN_PASSWORD", "DevAdmin123")


class AgentConsoleLoginTests(unittest.TestCase):
    def setUp(self) -> None:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.session = requests.Session()
        self.session.verify = False

    def test_static_agent_login_starts_without_eccp_agent_number_error(self) -> None:
        try:
            login_page = self.session.get(f"{BASE_URL}/", timeout=10)
        except requests.RequestException as exc:
            self.skipTest(f"Issabel runtime not reachable: {exc}")
            return

        self.assertEqual(login_page.status_code, 200)

        auth = self.session.post(
            f"{BASE_URL}/",
            data={
                "input_user": WEB_ADMIN_USER,
                "input_pass": WEB_ADMIN_PASSWORD,
                "submit_login": "Submit",
            },
            timeout=10,
        )
        self.assertEqual(auth.status_code, 200)

        response = self.session.post(
            f"{BASE_URL}/index.php?menu=call_center&rawmode=yes",
            data={
                "menu": "call_center",
                "rawmode": "yes",
                "action": "doLogin",
                "agent": "Agent/1",
                "ext": "1001",
                "ext_callback": "",
                "pass_callback": "",
                "callback": "false",
            },
            timeout=10,
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertTrue(payload["status"], payload["message"])
        self.assertNotIn("Invalid agent number", payload["message"])

    def test_dynamic_sip_agent_login_starts_without_eccp_agent_number_error(self) -> None:
        try:
            login_page = self.session.get(f"{BASE_URL}/", timeout=10)
        except requests.RequestException as exc:
            self.skipTest(f"Issabel runtime not reachable: {exc}")
            return

        self.assertEqual(login_page.status_code, 200)

        auth = self.session.post(
            f"{BASE_URL}/",
            data={
                "input_user": WEB_ADMIN_USER,
                "input_pass": WEB_ADMIN_PASSWORD,
                "submit_login": "Submit",
            },
            timeout=10,
        )
        self.assertEqual(auth.status_code, 200)

        response = self.session.post(
            f"{BASE_URL}/index.php?menu=call_center&rawmode=yes",
            data={
                "menu": "call_center",
                "rawmode": "yes",
                "action": "doLogin",
                "agent": "SIP/1001",
                "ext": "1001",
                "ext_callback": "",
                "pass_callback": "",
                "callback": "false",
            },
            timeout=10,
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertTrue(payload["status"], payload["message"])
        self.assertNotIn("Invalid agent number", payload["message"])

    def test_agent_console_prefers_legacy_agent_when_both_agent_and_sip_exist(self) -> None:
        try:
            login_page = self.session.get(f"{BASE_URL}/", timeout=10)
        except requests.RequestException as exc:
            self.skipTest(f"Issabel runtime not reachable: {exc}")
            return

        self.assertEqual(login_page.status_code, 200)

        auth = self.session.post(
            f"{BASE_URL}/",
            data={
                "input_user": WEB_ADMIN_USER,
                "input_pass": WEB_ADMIN_PASSWORD,
                "submit_login": "Submit",
            },
            timeout=10,
        )
        self.assertEqual(auth.status_code, 200)

        response = self.session.post(
            f"{BASE_URL}/index.php?menu=call_center&rawmode=yes",
            data={
                "menu": "call_center",
                "rawmode": "yes",
                "action": "doLogout",
            },
            timeout=10,
        )
        self.assertEqual(response.status_code, 200)
        html = response.text

        if 'value="Agent/1"' not in html or 'value="SIP/1001"' not in html:
            self.skipTest("runtime does not expose both Agent/1 and SIP/1001 in selector")
            return

        match = re.search(r'<option value="([^"]+)"[^>]*selected="selected"', html)
        self.assertIsNotNone(match, "no selected agent option found")
        self.assertEqual(match.group(1), "Agent/1")


if __name__ == "__main__":
    unittest.main()
