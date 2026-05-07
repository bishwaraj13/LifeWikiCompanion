from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
from pathlib import Path
from typing import Protocol

from app.codex_bridge.runner import CodexRunResult
from app.wiki_engine.paths import LifeWikiPaths


class CodexPromptRunner(Protocol):
    def is_available(self) -> bool:
        ...

    def run_prompt(self, prompt: str, timeout_seconds: int = 120) -> CodexRunResult:
        ...


@dataclass(frozen=True)
class CompanionResponse:
    text: str
    raw_conversation_path: Path
    memory_pages: list[Path]


class CompanionService:
    def __init__(self, paths: LifeWikiPaths, runner: CodexPromptRunner | None = None, repo_root: Path | None = None):
        self.paths = paths
        self.runner = runner
        self.repo_root = repo_root or Path(__file__).resolve().parents[2]
        self.paths.ensure_base_dirs()

    def reflect(self, message: str, at: str | None = None) -> CompanionResponse:
        timestamp = at or datetime.now().astimezone().isoformat(timespec="seconds")
        raw_path = self._append_raw_conversation(message, timestamp)
        raw_before = self._raw_fingerprints()
        response_text = self._codex_response(message, timestamp, raw_path) or self._fallback_response(message)
        raw_after = self._raw_fingerprints()
        if raw_before != raw_after:
            raise RuntimeError("Codex companion reflection changed files under raw/. Refusing to continue.")

        return CompanionResponse(
            text=response_text,
            raw_conversation_path=raw_path,
            memory_pages=[],
        )

    def _append_raw_conversation(self, message: str, timestamp: str) -> Path:
        date = timestamp[:10]
        path = self.paths.companion_conversations_dir / f"{date}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as file:
            if path.stat().st_size == 0:
                file.write(f"# Companion conversation for {date}\n")
            file.write(f"\n## {timestamp}\n\nUser:\n{message.rstrip()}\n")
        return path

    def _codex_response(self, message: str, timestamp: str, raw_path: Path) -> str:
        if not self.runner or not self.runner.is_available():
            return ""
        prompt = self._build_prompt(message, timestamp, raw_path)
        result = self.runner.run_prompt(prompt, timeout_seconds=300)
        if result.returncode != 0:
            raise RuntimeError(f"Codex companion reflection failed: {result.stderr.strip() or result.stdout.strip()}")
        return result.stdout.strip()

    def _build_prompt(self, message: str, timestamp: str, raw_path: Path) -> str:
        sections = [
            "# LifeWiki Companion Reflection",
            "",
            f"Timestamp: {timestamp}",
            "",
            "You are Codex acting as the user's LifeWiki companion.",
            "",
            "## Companion Personality",
            "",
            "- Speak like a steady, curious thinking partner who remembers the user's life context.",
            "- Reflect patterns in the user's words instead of merely confirming that input was saved.",
            "- Ask one grounded follow-up question when it would help the conversation continue.",
            "- Keep questions specific to the user's projects, constraints, energy, or learning interests.",
            "- Avoid turning reflections into a task list unless the user asks for planning or `/now`.",
            "",
            "## Repository Rules",
            "",
            self._read_optional(self.repo_root / "AGENTS.md").strip(),
            "",
            "## Companion Reflection Prompt",
            "",
            self._read_optional(self.repo_root / "schema/prompts/companion_reflection.md").strip(),
            "",
            "## Relevant Wiki Context",
            "",
            self._wiki_context().strip() or "No wiki context exists yet.",
            "",
            "## Raw Conversation Just Preserved",
            "",
            raw_path.relative_to(self.paths.root).as_posix(),
            "",
            "```text",
            message,
            "```",
            "",
            "## Task",
            "",
            "- Preserve every file under `raw/` exactly as-is.",
            "- Update only useful distilled pages under `wiki/` when this message changes life context.",
            "- Reply conversationally using the companion reflection prompt.",
            "- Do not force a next action unless the user explicitly asks for one.",
        ]
        return "\n".join(sections)

    def _wiki_context(self, max_chars: int = 12000) -> str:
        if not self.paths.wiki_dir.exists():
            return ""
        chunks = []
        for path in sorted(self.paths.wiki_dir.rglob("*.md")):
            relative = path.relative_to(self.paths.root).as_posix()
            text = path.read_text(encoding="utf-8", errors="replace").strip()
            if text:
                chunks.append(f"### {relative}\n\n```markdown\n{text[:3000]}\n```")
        context = "\n\n".join(chunks)
        if len(context) <= max_chars:
            return context
        return context[-max_chars:]

    def _read_optional(self, path: Path) -> str:
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def _raw_fingerprints(self) -> dict[str, str]:
        if not self.paths.raw_dir.exists():
            return {}
        fingerprints = {}
        for path in sorted(item for item in self.paths.raw_dir.rglob("*") if item.is_file()):
            relative = path.relative_to(self.paths.root).as_posix()
            fingerprints[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        return fingerprints

    def _fallback_response(self, message: str) -> str:
        lower = message.lower()
        if any(word in lower for word in ("routine", "morning", "mornings", "wake", "breakfast")):
            return (
                "I hear you. Your mornings sound like they are setting the emotional tone for the whole day, "
                "so it makes sense that once they go sideways, everything after that feels heavier. "
                "For now I am saving the pattern: mornings need gentler structure, not more pressure. "
                "What part of the morning usually starts the slide?"
            )
        if any(word in lower for word in ("scattered", "overwhelmed", "behind", "stuck", "messy")):
            return (
                "I hear you. That scattered feeling sounds less like laziness and more like too many open loops "
                "competing for the same small bit of attention. I will hold this as context, without turning it "
                "into a todo list right away. Which loop feels loudest right now?"
            )
        if any(word in lower for word in ("happy", "good", "excited", "proud")):
            return (
                "I like hearing this. I am saving it as part of the picture too, because your wiki should remember "
                "what gives you energy, not only what drains it. What made this feel energizing?"
            )
        return (
            "I hear you. I have saved this as part of your life context, and I will let it inform future reflections "
            "and recommendations without forcing it into a task. What part of this should we understand better next?"
        )
