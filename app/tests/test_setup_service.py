import tempfile
import unittest
from pathlib import Path

from app.services.setup_service import SetupRequiredError, SetupService
from app.wiki_engine.paths import LifeWikiPaths


class SetupServiceTests(unittest.TestCase):
    def test_setup_creates_local_config_and_required_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = LifeWikiPaths(Path(tmp))
            service = SetupService(paths)

            profile = service.setup(
                user_name="Bishwaraj",
                telegram_user_id="12345",
                codex_command="/usr/bin/codex",
            )

            self.assertEqual(profile.user_name, "Bishwaraj")
            self.assertEqual(profile.telegram_user_id, "12345")
            self.assertEqual(profile.llm_backend, "codex-cli")
            self.assertTrue((Path(tmp) / "system/config.json").exists())
            self.assertTrue((Path(tmp) / "raw").exists())
            self.assertTrue((Path(tmp) / "wiki").exists())

    def test_interactions_require_setup(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = SetupService(LifeWikiPaths(Path(tmp)))

            with self.assertRaises(SetupRequiredError):
                service.require_setup()

            service.setup(user_name="Bishwaraj")
            profile = service.require_setup()
            self.assertEqual(profile.user_name, "Bishwaraj")

    def test_telegram_sender_must_match_configured_user_when_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = SetupService(LifeWikiPaths(Path(tmp)))
            service.setup(user_name="Bishwaraj", telegram_user_id="12345")

            self.assertTrue(service.is_telegram_user_allowed("12345"))
            self.assertFalse(service.is_telegram_user_allowed("99999"))


if __name__ == "__main__":
    unittest.main()
