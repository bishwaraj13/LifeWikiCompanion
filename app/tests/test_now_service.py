import tempfile
import unittest
from pathlib import Path

from app.codex_bridge.runner import CodexRunResult
from app.services.now_service import NowService
from app.wiki_engine.paths import LifeWikiPaths


class FakeCodexRunner:
    def __init__(self):
        self.prompts = []

    def is_available(self):
        return True

    def run_prompt(self, prompt, timeout_seconds=120):
        self.prompts.append(prompt)
        return CodexRunResult(
            0,
            "\n".join(
                [
                    "Do this one thing now:",
                    "Write a rough README outline",
                    "",
                    "Timebox: 20 minutes.",
                    "Stop when: A rough outline exists, even if it is incomplete.",
                ]
            ),
            "",
        )


class NowServiceTests(unittest.TestCase):
    def test_recommend_now_prefers_codex_prompt_and_writes_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = LifeWikiPaths(root)
            project = root / "wiki/projects/aws-vector-db-mcp.md"
            project.parent.mkdir(parents=True, exist_ok=True)
            project.write_text(
                "\n".join(
                    [
                        "---",
                        "type: project",
                        "priority: high",
                        "energy_required: low",
                        "---",
                        "# AWS Vector DB MCP",
                        "## Next possible actions",
                        "- [ ] Write a rough README outline",
                        "- [ ] Design the full database schema",
                    ]
                ),
                encoding="utf-8",
            )

            runner = FakeCodexRunner()
            service = NowService(paths, runner=runner)
            recommendation = service.recommend_now(
                energy="low",
                available_minutes=20,
                mental_state="foggy",
                at="2026-05-06T10:00:00+05:30",
            )

            self.assertEqual(recommendation.action, "Write a rough README outline")
            self.assertEqual(recommendation.timebox_minutes, 20)
            self.assertNotIn("\n- [ ]", recommendation.action)
            self.assertEqual(len(runner.prompts), 1)
            self.assertIn("Recommend Now Prompt", runner.prompts[0])
            self.assertIn("Write a rough README outline", runner.prompts[0])
            self.assertIn("Energy: low", runner.prompts[0])

            next_action = root / "wiki/now/next-action.md"
            self.assertTrue(next_action.exists())
            text = next_action.read_text(encoding="utf-8")
            self.assertIn("Action: Write a rough README outline", text)
            self.assertIn("Timebox: 20 minutes", text)
            self.assertIn("Stop condition:", text)


if __name__ == "__main__":
    unittest.main()
