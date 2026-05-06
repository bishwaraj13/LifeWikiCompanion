import tempfile
import unittest
from pathlib import Path

from app.services.capture_service import CaptureService
from app.wiki_engine.paths import LifeWikiPaths


class CaptureServiceTests(unittest.TestCase):
    def test_telegram_capture_appends_raw_markdown_and_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = LifeWikiPaths(Path(tmp))
            service = CaptureService(paths)

            first = service.capture_telegram_message("I watched boto3 and CDK lecture", at="2026-05-06T09:30:00+05:30")
            second = service.capture_telegram_message("Still confused about Terraform", at="2026-05-06T09:45:00+05:30")

            capture_file = Path(tmp) / "raw/telegram/captures/2026-05-06.md"
            self.assertEqual(first.raw_markdown_path, capture_file)
            self.assertEqual(second.raw_markdown_path, capture_file)

            text = capture_file.read_text(encoding="utf-8")
            self.assertIn("I watched boto3 and CDK lecture", text)
            self.assertIn("Still confused about Terraform", text)
            self.assertLess(text.index("I watched boto3"), text.index("Still confused"))

            jsonl = (Path(tmp) / "raw/telegram/messages.jsonl").read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(jsonl), 2)
            self.assertIn('"source": "telegram"', jsonl[0])


if __name__ == "__main__":
    unittest.main()
