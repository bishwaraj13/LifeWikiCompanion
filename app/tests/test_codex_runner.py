import unittest
import tempfile
from pathlib import Path

from app.codex_bridge.runner import CodexRunner
from app.services.setup_service import SetupProfile


class CodexRunnerTests(unittest.TestCase):
    def test_runner_reports_unavailable_when_codex_command_missing(self):
        profile = SetupProfile(
            user_name="Bishwaraj",
            telegram_user_id="",
            llm_backend="none",
            codex_command="",
            created_at="2026-05-06T00:00:00+05:30",
        )

        runner = CodexRunner(profile, Path("/tmp/lifewiki"))

        self.assertFalse(runner.is_available())
        with self.assertRaises(RuntimeError):
            runner.run_prompt("hello")

    def test_runner_uses_codex_exec_in_the_data_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake_codex = root / "fake_codex.py"
            fake_codex.write_text(
                "\n".join(
                    [
                        "#!/usr/bin/env python3",
                        "import os",
                        "import sys",
                        "print('|'.join(sys.argv[1:]))",
                        "print(os.getcwd())",
                        "print(sys.stdin.read())",
                    ]
                ),
                encoding="utf-8",
            )
            fake_codex.chmod(0o755)
            profile = SetupProfile(
                user_name="Bishwaraj",
                telegram_user_id="",
                llm_backend="codex-cli",
                codex_command=str(fake_codex),
                created_at="2026-05-06T00:00:00+05:30",
            )

            result = CodexRunner(profile, root).run_prompt("maintain the wiki")

            self.assertEqual(result.returncode, 0)
            self.assertIn(f"exec|-C|{root}|--skip-git-repo-check|-", result.stdout)
            self.assertIn("maintain the wiki", result.stdout)


if __name__ == "__main__":
    unittest.main()
