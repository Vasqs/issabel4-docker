import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NEWIVR_ROOT = ROOT / "overlays" / "NewIvr"
DASCH_ROOT = NEWIVR_ROOT / "web_root" / "NewIvr" / "dasch"


def read_legacy_text(path: Path) -> str:
    return path.read_text(encoding="latin-1")


class NewIvrWhatsAppZApiTests(unittest.TestCase):
    def test_overlay_hook_provisions_whatsapp_provider_columns(self) -> None:
        hook = NEWIVR_ROOT / "hooks" / "apply.sh"
        text = hook.read_text()

        self.assertIn("whatssconfig", text)
        self.assertIn("provider_key", text)
        self.assertIn("credentials", text)
        self.assertIn("ura_configurations", text)
        self.assertIn("whatsapp_api_id", text)

    def test_php_helper_declares_zapi_provider_contract(self) -> None:
        helper = DASCH_ROOT / "whatsapp_provider_helper.php"
        self.assertTrue(helper.exists(), "NewIvr must have a central WhatsApp provider helper")
        text = read_legacy_text(helper)

        self.assertIn("function newivr_whatsapp_normalize_phone", text)
        self.assertIn("function newivr_whatsapp_send_whaticket", text)
        self.assertIn("function newivr_whatsapp_send_zapi", text)
        self.assertIn("function newivr_whatsapp_check_zapi_connection", text)
        self.assertIn("send-text", text)
        self.assertIn("status", text)
        self.assertIn("Client-Token", text)
        self.assertIn("instance_id", text)
        self.assertIn("instance_token", text)
        self.assertNotIn("??", text, "helper must stay compatible with PHP 5.4")
        self.assertNotRegex(text, re.compile(r"function\s+\w+\([^)]*\)\s*:\s*"))

    def test_whatss2_keeps_legacy_args_and_accepts_optional_config_id(self) -> None:
        text = read_legacy_text(DASCH_ROOT / "whatss2.php")

        self.assertIn("<phone> <nome> <token> <url> <mensagem> [config_id]", text)
        self.assertIn("whatsapp_provider_helper.php", text)
        self.assertIn("newivr_whatsapp_send_with_optional_config", text)
        self.assertIn("api/messages/send", text, "legacy Whaticket endpoint must remain available")

    def test_get_whatsapp_apis_keeps_names_and_adds_metadata(self) -> None:
        text = read_legacy_text(DASCH_ROOT / "get_whatsapp_apis.php")

        self.assertIn("'apis'", text)
        self.assertIn("'configs'", text)
        self.assertIn("provider_key", text)
        self.assertIn("status", text)
        self.assertIn("ConectionName", text)

    def test_ura_flow_persists_and_passes_whatsapp_api_id(self) -> None:
        create_project = read_legacy_text(DASCH_ROOT / "creatprojeto.php")
        ivr_custom = read_legacy_text(DASCH_ROOT / "ivr_custom.php")
        index = read_legacy_text(DASCH_ROOT / "index_ura1.html")
        agi = NEWIVR_ROOT / "web_root" / "scripts_ura" / "digito.php"

        self.assertIn("whatsapp_api_id", create_project)
        self.assertIn("whatsapp_api_id", ivr_custom)
        self.assertIn("digito.php", ivr_custom)
        self.assertRegex(ivr_custom, re.compile(r"digito\.php[^\n]+whatsapp_api_id"))
        self.assertIn("whatsapp_api_id", index)
        self.assertIn("provider", index)
        self.assertTrue(agi.exists(), "WhatsApp digit AGI wrapper must be versioned")
        agi_text = read_legacy_text(agi)
        self.assertIn("whatsapp_api_id", agi_text)
        self.assertIn("newivr_whatsapp_send_with_optional_config", agi_text)

    def test_admin_screen_exposes_provider_specific_zapi_fields(self) -> None:
        html = read_legacy_text(DASCH_ROOT / "dasch_prod" / "whatssconfig.html")
        handler = read_legacy_text(DASCH_ROOT / "dasch_prod" / "whatsapp_api_handler.php")

        for expected in [
            "provider_key",
            "whaticket",
            "zapi",
            "instance_id",
            "instance_token",
            "client_token",
        ]:
            self.assertIn(expected, html)
            self.assertIn(expected, handler)

        self.assertIn("credentials", handler)
        self.assertIn("newivr_whatsapp_check_connection", handler)

    def test_zapi_admin_form_uses_instance_credentials_without_required_legacy_token(self) -> None:
        html = read_legacy_text(DASCH_ROOT / "dasch_prod" / "whatssconfig.html")
        handler = read_legacy_text(DASCH_ROOT / "dasch_prod" / "whatsapp_api_handler.php")

        self.assertIn("https://api.z-api.io", html)
        self.assertIn("applyProviderFieldState", html)
        self.assertIn("instanceId.required", html)
        self.assertIn("instanceToken.required", html)
        self.assertIn("clientToken.required = false", html)
        self.assertIn("token.required = provider !== 'zapi'", html)
        self.assertIn("token.disabled = provider === 'zapi'", html)
        self.assertIn("document.querySelectorAll('.zapi-field')", html)
        self.assertIn("const zapiDefaultUrl = 'https://api.z-api.io'", html)
        self.assertIn("url.value = zapiDefaultUrl", html)
        self.assertIn("instance_token: formData.get('instance_token') || ''", html)
        self.assertNotIn("instance_token: formData.get('instance_token') || formData.get('token')", html)
        self.assertIn("'base_url' => isset($data['url']) && trim($data['url']) !== '' ? $data['url'] : 'https://api.z-api.io'", handler)
        self.assertIn("'instance_token' => isset($data['instance_token']) ? $data['instance_token'] : ''", handler)
        self.assertNotIn("isset($data['instance_token']) ? $data['instance_token'] : (isset($data['token'])", handler)
        self.assertIn("$provider = isset($data['provider_key'])", handler)
        self.assertIn("array('ApiName', 'url', 'sendnumber', 'ConectionName', 'campaings_id', 'instance_id', 'instance_token')", handler)
        self.assertIn("array('ApiName', 'url', 'token', 'sendnumber', 'ConectionName', 'campaings_id')", handler)

    def test_admin_handler_tolerates_legacy_whatsapp_config_schema(self) -> None:
        handler = read_legacy_text(DASCH_ROOT / "dasch_prod" / "whatsapp_api_handler.php")

        self.assertIn("whatsappConfigColumnsExist", handler)
        self.assertRegex(handler, re.compile(r"SELECT id, ApiName, url, token, sendnumber, ConectionName, status, sendcount, alert, campaings_id\s+FROM whatssconfig"))
        self.assertRegex(handler, re.compile(r"\['provider_key'\]\s*=\s*'whaticket'"))
        self.assertRegex(handler, re.compile(r"\['credentials'\]\s*=\s*''"))
        self.assertIn("JSON_PARTIAL_OUTPUT_ON_ERROR", handler)

    def test_admin_handler_migrates_runtime_schema_before_writes(self) -> None:
        handler = read_legacy_text(DASCH_ROOT / "dasch_prod" / "whatsapp_api_handler.php")

        self.assertIn("function ensureWhatsappProviderSchema", handler)
        self.assertIn("ALTER TABLE whatssconfig ADD COLUMN provider_key", handler)
        self.assertIn("ALTER TABLE whatssconfig ADD COLUMN credentials", handler)
        self.assertIn("ensureWhatsappProviderSchema($pdo);", handler)
        self.assertLess(
            handler.index("ensureWhatsappProviderSchema($pdo);"),
            handler.index("INSERT INTO whatssconfig"),
            "createConfig must migrate the connected runtime DB before inserting provider fields",
        )
        self.assertIn(
            'ensureWhatsappProviderSchema($pdo);\n        $sql = "UPDATE whatssconfig',
            handler,
        )

    def test_admin_test_connection_sends_id_in_data_payload(self) -> None:
        html = read_legacy_text(DASCH_ROOT / "dasch_prod" / "whatssconfig.html")
        handler = read_legacy_text(DASCH_ROOT / "dasch_prod" / "whatsapp_api_handler.php")

        self.assertIn("action: 'testConnection'", html)
        self.assertIn("data: {", html)
        self.assertIn("id: currentTestConfig.id", html)
        self.assertNotIn("configId: currentTestConfig.id,\n                        phoneNumber", html)
        self.assertIn("isset($data['id'])", handler)
        self.assertIn("isset($data['configId'])", handler)

    def test_admin_test_connection_sends_real_test_message(self) -> None:
        html = read_legacy_text(DASCH_ROOT / "dasch_prod" / "whatssconfig.html")
        handler = read_legacy_text(DASCH_ROOT / "dasch_prod" / "whatsapp_api_handler.php")

        self.assertIn("$phoneNumber = isset($data['phoneNumber'])", handler)
        self.assertIn("$contactName = isset($data['contactName'])", handler)
        self.assertIn("newivr_whatsapp_send_with_optional_config(", handler)
        self.assertIn("'send_result' => $sendResult", handler)
        self.assertIn("'status_result' => $statusResult", handler)
        self.assertIn("Mensagem de teste enviada", handler)
        self.assertIn("Falha ao enviar mensagem de teste", handler)
        self.assertIn("showTestResult(result.message || 'Mensagem de teste enviada com sucesso.'", html)


if __name__ == "__main__":
    unittest.main()
