import tempfile
import unittest
from pathlib import Path

from app.services.source_ingest_service import SourceIngestService
from app.wiki_engine.paths import LifeWikiPaths


class SourceIngestServiceTests(unittest.TestCase):
    def test_ingest_text_document_preserves_raw_file_and_creates_source_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "downloaded-note.txt"
            source.write_text("AWS Bedrock notes\n\nAgents need tools and memory.", encoding="utf-8")

            result = SourceIngestService(LifeWikiPaths(root)).ingest_document(source)

            self.assertEqual(result.raw_path, root / "raw/files/downloaded-note.txt")
            self.assertEqual(result.note_path, root / "wiki/sources/downloaded-note.md")
            self.assertTrue(result.raw_path.exists())
            note = result.note_path.read_text(encoding="utf-8")
            self.assertIn("type: source-note", note)
            self.assertIn("source_type: document", note)
            self.assertIn("raw/files/downloaded-note.txt", note)
            self.assertIn("Agents need tools and memory.", note)

    def test_ingest_webpage_preserves_html_and_creates_readable_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            html = """
            <html>
              <head><title>Vector Search Basics</title><script>ignored()</script></head>
              <body><h1>Vector Search Basics</h1><p>Embeddings make semantic lookup possible.</p></body>
            </html>
            """

            result = SourceIngestService(LifeWikiPaths(root)).ingest_webpage(
                "https://example.com/vector-search",
                html=html,
                captured_on="2026-05-06",
            )

            self.assertEqual(result.raw_path, root / "raw/web_clips/2026-05-06-vector-search-basics.html")
            self.assertEqual(result.note_path, root / "wiki/sources/vector-search-basics.md")
            self.assertTrue(result.raw_path.exists())
            note = result.note_path.read_text(encoding="utf-8")
            self.assertIn("source_type: webpage", note)
            self.assertIn("source_url: https://example.com/vector-search", note)
            self.assertIn("Embeddings make semantic lookup possible.", note)
            self.assertNotIn("ignored()", note)

    def test_ingest_pdf_preserves_raw_even_without_pdf_text_dependency(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = root / "paper.pdf"
            pdf.write_bytes(b"%PDF-1.4\n% tiny placeholder\n")

            result = SourceIngestService(LifeWikiPaths(root)).ingest_document(pdf)

            self.assertEqual(result.raw_path, root / "raw/files/paper.pdf")
            self.assertTrue(result.raw_path.exists())
            note = result.note_path.read_text(encoding="utf-8")
            self.assertIn("source_type: pdf", note)
            self.assertIn("raw/files/paper.pdf", note)
            self.assertIn("PDF text extraction", note)


if __name__ == "__main__":
    unittest.main()
