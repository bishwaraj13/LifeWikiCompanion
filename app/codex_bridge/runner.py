from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess

from app.services.setup_service import SetupProfile


@dataclass(frozen=True)
class CodexRunResult:
    returncode: int
    stdout: str
    stderr: str


class CodexRunner:
    def __init__(self, profile: SetupProfile, data_root: Path):
        self.profile = profile
        self.data_root = data_root

    def is_available(self) -> bool:
        return bool(self.profile.codex_command)

    def run_prompt(self, prompt: str, timeout_seconds: int = 120) -> CodexRunResult:
        if not self.profile.codex_command:
            raise RuntimeError("Codex CLI is not configured. Run setup after installing and authenticating Codex.")

        completed = subprocess.run(
            [self.profile.codex_command, "exec", "-C", str(self.data_root), "--skip-git-repo-check", "-"],
            input=prompt,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            cwd=self.data_root,
            check=False,
        )
        return CodexRunResult(completed.returncode, completed.stdout, completed.stderr)
