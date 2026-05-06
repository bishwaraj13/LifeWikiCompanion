import tempfile
import unittest
from pathlib import Path

from app.services.learning_service import LearningService
from app.wiki_engine.paths import LifeWikiPaths


class LearningServiceTests(unittest.TestCase):
    def test_ingest_lecture_notes_preserves_raw_and_creates_wiki_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = LifeWikiPaths(Path(tmp))
            service = LearningService(paths)

            result = service.ingest_lecture_notes(
                title="Boto3 vs CDK",
                topic="AWS",
                notes="boto3 is imperative. CDK is infrastructure as code. Terraform is provider neutral.",
                watched_on="2026-05-06",
                related_learning=["boto3", "AWS CDK", "Terraform"],
                related_projects=["AWS Vector DB MCP"],
            )

            raw_note = Path(tmp) / "raw/lectures/notes/2026-05-06-boto3-vs-cdk.md"
            lecture_page = Path(tmp) / "wiki/lectures/aws/2026-05-06-boto3-vs-cdk.md"
            boto3_page = Path(tmp) / "wiki/learning/boto3.md"

            self.assertEqual(result.raw_note_path, raw_note)
            self.assertEqual(result.lecture_page_path, lecture_page)
            self.assertTrue(raw_note.exists())
            self.assertTrue(lecture_page.exists())
            self.assertTrue(boto3_page.exists())

            lecture_text = lecture_page.read_text(encoding="utf-8")
            self.assertIn("type: lecture-note", lecture_text)
            self.assertIn("[[boto3]]", lecture_text)
            self.assertIn("[[AWS Vector DB MCP]]", lecture_text)
            self.assertIn("raw/lectures/notes/2026-05-06-boto3-vs-cdk.md", lecture_text)

            learning_text = boto3_page.read_text(encoding="utf-8")
            self.assertIn("type: learning-topic", learning_text)
            self.assertIn("## Next study action", learning_text)


if __name__ == "__main__":
    unittest.main()
