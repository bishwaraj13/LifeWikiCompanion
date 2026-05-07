import tempfile
import unittest
from pathlib import Path

from app.codex_bridge.runner import CodexRunResult
from app.services.companion_service import CompanionService
from app.wiki_engine.paths import LifeWikiPaths


class FakeCodexRunner:
    def __init__(self, stdout="I hear you. I am saving this as context: mornings need gentler structure."):
        self.stdout = stdout
        self.prompts = []

    def is_available(self):
        return True

    def run_prompt(self, prompt, timeout_seconds=120):
        self.prompts.append(prompt)
        return CodexRunResult(0, self.stdout, "")


class CompanionServiceTests(unittest.TestCase):
    def test_reflection_preserves_conversation_and_uses_codex_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runner = FakeCodexRunner()
            service = CompanionService(LifeWikiPaths(root), runner=runner)

            response = service.reflect(
                "My mornings are messy. I wake up late, skip breakfast, and then feel behind all day.",
                at="2026-05-06T08:20:00+05:30",
            )

            raw = root / "raw/companion/conversations/2026-05-06.md"

            self.assertTrue(raw.exists())
            self.assertIn("My mornings are messy", raw.read_text(encoding="utf-8"))

            self.assertEqual(len(runner.prompts), 1)
            self.assertIn("Companion Reflection Prompt", runner.prompts[0])
            self.assertIn("raw/companion/conversations/2026-05-06.md", runner.prompts[0])
            self.assertIn("My mornings are messy", runner.prompts[0])
            self.assertIn("I hear you", response.text)
            self.assertEqual(response.memory_pages, [])

    def test_companion_response_does_not_force_a_next_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner = FakeCodexRunner(stdout="I hear you. That scattered feeling sounds heavy, and I am saving it as context.")
            service = CompanionService(LifeWikiPaths(Path(tmp)), runner=runner)

            response = service.reflect(
                "I just want to talk about how scattered I feel, not make a todo list.",
                at="2026-05-06T21:00:00+05:30",
            )

            self.assertNotIn("Do this one thing now", response.text)
            self.assertNotIn("Timebox:", response.text)
            self.assertIn("scattered", response.text)

    def test_fallback_response_keeps_conversation_two_way(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = CompanionService(LifeWikiPaths(Path(tmp)), runner=None)

            response = service.reflect(
                "I am trying to balance Festo work, screencast-refiner, and learning VLA.",
                at="2026-05-06T21:30:00+05:30",
            )

            self.assertIn("saved", response.text.lower())
            self.assertIn("?", response.text)

    def test_prompt_defines_companion_personality_and_two_way_reply(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner = FakeCodexRunner(stdout="I hear you. What part should we untangle first?")
            service = CompanionService(LifeWikiPaths(Path(tmp)), runner=runner)

            service.reflect(
                "I want the companion to talk back, not just capture input.",
                at="2026-05-06T22:00:00+05:30",
            )

            prompt = runner.prompts[0]
            self.assertIn("Companion Personality", prompt)
            self.assertIn("Ask one grounded follow-up question", prompt)


if __name__ == "__main__":
    unittest.main()
