import unittest
from pathlib import Path

from app.wiki_engine.frontmatter import dump_frontmatter, parse_frontmatter
from app.wiki_engine.wikilinks import slugify_title, wikilink_target


class FrontmatterAndWikiLinkTests(unittest.TestCase):
    def test_frontmatter_round_trip_preserves_body(self):
        text = dump_frontmatter(
            {
                "type": "learning-topic",
                "status": "active",
                "tags": ["learning", "aws"],
                "source": ["raw/telegram/captures/2026-05-06.md"],
            },
            "# AWS\n\n## Current understanding\n",
        )

        metadata, body = parse_frontmatter(text)

        self.assertEqual(metadata["type"], "learning-topic")
        self.assertEqual(metadata["tags"], ["learning", "aws"])
        self.assertEqual(metadata["source"], ["raw/telegram/captures/2026-05-06.md"])
        self.assertEqual(body, "# AWS\n\n## Current understanding\n")

    def test_wikilinks_resolve_to_expected_local_pages(self):
        self.assertEqual(slugify_title("AWS Vector DB MCP"), "aws-vector-db-mcp")
        self.assertEqual(
            wikilink_target("[[AWS Vector DB MCP]]", {"aws-vector-db-mcp": Path("wiki/projects/aws-vector-db-mcp.md")}),
            Path("wiki/projects/aws-vector-db-mcp.md"),
        )


if __name__ == "__main__":
    unittest.main()
