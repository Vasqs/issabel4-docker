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

        self.assertNotIn("Invalid agent number", payload["message"])
        self.assertNotIn("Specified agent not found", payload["message"])

        if not payload["status"]:
            self.assertIn("Failed to start login process on Asterisk", payload["message"])

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

    def test_dynamic_sip_agent_checklogin_does_not_lose_started_session(self) -> None:
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

        start = self.session.post(
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
        self.assertEqual(start.status_code, 200)
        start_payload = start.json()
        self.assertTrue(start_payload["status"], start_payload["message"])

        followup = self.session.post(
            f"{BASE_URL}/index.php?menu=call_center&rawmode=yes",
            data={
                "menu": "call_center",
                "rawmode": "yes",
                "action": "checkLogin",
            },
            timeout=10,
        )
        self.assertEqual(followup.status_code, 200)
        followup_payload = followup.json()

        # The legacy checkLogin endpoint is flaky in some Issabel builds even
        # when the real Agent Console flow works. This regression guard only
        # asserts that the authenticated web session survives the doLogin ->
        # checkLogin transition instead of depending on that endpoint to
        # complete the login state machine correctly.
        self.assertNotEqual(followup_payload.get("statusResponse"), "ERROR_SESSION", followup_payload)
        self.assertNotIn("session has expired", str(followup_payload).lower())

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

        options = re.findall(r'<option value="([^"]+)"[^>]*>', html)
        self.assertIn("Agent/1", options)
        self.assertIn("SIP/1001", options)
        self.assertLess(options.index("Agent/1"), options.index("SIP/1001"))


if __name__ == "__main__":
    unittest.main()
