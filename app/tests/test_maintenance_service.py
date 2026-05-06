import tempfile
import unittest
from pathlib import Path

from app.codex_bridge.runner import CodexRunResult
from app.services.capture_service import CaptureService
from app.services.maintenance_service import MaintenanceService
from app.wiki_engine.paths import LifeWikiPaths


class FakeCodexRunner:
    def __init__(self):
        self.prompts = []

    def is_available(self):
        return True

    def run_prompt(self, prompt, timeout_seconds=120):
        self.prompts.append(prompt)
        return CodexRunResult(0, "wiki updated", "")


class MaintenanceServiceTests(unittest.TestCase):
    def test_maintenance_invokes_codex_for_new_raw_captures_and_records_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = LifeWikiPaths(root)
            CaptureService(paths).capture_telegram_message(
                "I need to integrate Codex as the LifeWiki maintainer.",
                at="2026-05-06T10:00:00+05:30",
            )
            runner = FakeCodexRunner()

            result = MaintenanceService(paths, runner).maintain(at="2026-05-06T10:05:00+05:30")

            self.assertTrue(result.ran_codex)
            self.assertEqual(result.raw_files_considered, ["raw/telegram/captures/2026-05-06.md", "raw/telegram/messages.jsonl"])
            self.assertEqual(len(runner.prompts), 1)
            self.assertIn("Preserve original user input under `raw/`.", runner.prompts[0])
            self.assertIn("raw/telegram/captures/2026-05-06.md", runner.prompts[0])
            self.assertIn("I need to integrate Codex", runner.prompts[0])
            self.assertTrue((root / "system/maintenance-state.json").exists())

    def test_maintenance_skips_codex_when_no_raw_files_changed(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = LifeWikiPaths(Path(tmp))
            CaptureService(paths).capture_telegram_message(
                "A first capture.",
                at="2026-05-06T10:00:00+05:30",
            )
            runner = FakeCodexRunner()
            service = MaintenanceService(paths, runner)

            first = service.maintain(at="2026-05-06T10:05:00+05:30")
            second = service.maintain(at="2026-05-06T10:10:00+05:30")

            self.assertTrue(first.ran_codex)
            self.assertFalse(second.ran_codex)
            self.assertEqual(second.raw_files_considered, [])
            self.assertEqual(len(runner.prompts), 1)


if __name__ == "__main__":
    unittest.main()
