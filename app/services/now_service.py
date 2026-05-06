from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
from typing import Protocol

from app.codex_bridge.runner import CodexRunResult
from app.wiki_engine.frontmatter import dump_frontmatter, parse_frontmatter
from app.wiki_engine.paths import LifeWikiPaths


class CodexPromptRunner(Protocol):
    def is_available(self) -> bool:
        ...

    def run_prompt(self, prompt: str, timeout_seconds: int = 120) -> CodexRunResult:
        ...


@dataclass(frozen=True)
class Recommendation:
    action: str
    timebox_minutes: int
    stop_condition: str
    source_page: Path
    reason: str


class NowService:
    def __init__(self, paths: LifeWikiPaths, runner: CodexPromptRunner | None = None, repo_root: Path | None = None):
        self.paths = paths
        self.runner = runner
        self.repo_root = repo_root or Path(__file__).resolve().parents[2]
        self.paths.ensure_base_dirs()

    def recommend_now(
        self,
        energy: str = "medium",
        available_minutes: int = 20,
        mental_state: str = "",
        at: str | None = None,
    ) -> Recommendation:
        codex_recommendation = self._codex_recommendation(energy, available_minutes, mental_state)
        if codex_recommendation:
            self._write_next_action(codex_recommendation, energy, mental_state, at)
            return codex_recommendation

        candidates = self._collect_candidates()
        if not candidates:
            fallback = Recommendation(
                action="Write a quick current-state check-in",
                timebox_minutes=min(available_minutes, 10),
                stop_condition="Energy, mental mode, available time, and one friction point are written down.",
                source_page=self.paths.now_dir / "current-state.md",
                reason="No open actions were found, so the useful first move is to refresh context.",
            )
            self._write_next_action(fallback, energy, mental_state, at)
            return fallback

        ranked = sorted(
            candidates,
            key=lambda candidate: self._score(candidate, energy, available_minutes),
            reverse=True,
        )
        action, source, metadata = ranked[0]
        recommendation = Recommendation(
            action=action,
            timebox_minutes=min(max(5, available_minutes), 25),
            stop_condition=self._stop_condition_for(action),
            source_page=source,
            reason=self._reason_for(source, metadata, energy),
        )
        self._write_next_action(recommendation, energy, mental_state, at)
        return recommendation

    def _codex_recommendation(self, energy: str, available_minutes: int, mental_state: str) -> Recommendation | None:
        if not self.runner or not self.runner.is_available():
            return None
        prompt = self._build_prompt(energy, available_minutes, mental_state)
        result = self.runner.run_prompt(prompt, timeout_seconds=300)
        if result.returncode != 0:
            raise RuntimeError(f"Codex /now recommendation failed: {result.stderr.strip() or result.stdout.strip()}")
        return self._parse_codex_recommendation(result.stdout, available_minutes)

    def _build_prompt(self, energy: str, available_minutes: int, mental_state: str) -> str:
        sections = [
            "# LifeWiki /now",
            "",
            "You are Codex recommending exactly one useful next action from the user's local Markdown wiki.",
            "",
            "## Recommend Now Prompt",
            "",
            self._read_optional(self.repo_root / "schema/prompts/recommend_now.md").strip(),
            "",
            "## Current State",
            "",
            f"Energy: {energy}",
            f"Available minutes: {available_minutes}",
            f"Mental state: {mental_state}",
            "",
            "## Candidate Wiki Context",
            "",
            self._action_context().strip() or "No open action context exists yet.",
            "",
            "## Task",
            "",
            "Return exactly one action using this shape:",
            "",
            "Do this one thing now:",
            "<action>",
            "",
            "Timebox: <minutes> minutes.",
            "Stop when: <clear stop condition>.",
        ]
        return "\n".join(sections)

    def _action_context(self, max_chars: int = 12000) -> str:
        chunks = []
        for folder in (self.paths.projects_dir, self.paths.learning_dir, self.paths.now_dir):
            if not folder.exists():
                continue
            for page in sorted(folder.rglob("*.md")):
                relative = page.relative_to(self.paths.root).as_posix()
                text = page.read_text(encoding="utf-8", errors="replace").strip()
                if text:
                    chunks.append(f"### {relative}\n\n```markdown\n{text[:3000]}\n```")
        context = "\n\n".join(chunks)
        if len(context) <= max_chars:
            return context
        return context[-max_chars:]

    def _parse_codex_recommendation(self, text: str, available_minutes: int) -> Recommendation:
        action = ""
        timebox = min(max(5, available_minutes), 25)
        stop_condition = "One visible, useful increment is finished."
        lines = [line.strip() for line in text.splitlines()]
        for index, line in enumerate(lines):
            if line.lower().startswith("do this one thing now"):
                remainder = line.partition(":")[2].strip()
                if remainder:
                    action = remainder
                else:
                    action = next((item for item in lines[index + 1 :] if item), "")
                break
        if not action:
            action = next((line for line in lines if line and not line.lower().startswith(("timebox:", "stop when:"))), "")
        for line in lines:
            if line.lower().startswith("timebox:"):
                match = re.search(r"\d+", line)
                if match:
                    timebox = int(match.group(0))
            if line.lower().startswith("stop when:"):
                stop_condition = line.partition(":")[2].strip().rstrip(".") or stop_condition
        if not action:
            action = "Write a quick current-state check-in"
        return Recommendation(
            action=action.rstrip("."),
            timebox_minutes=timebox,
            stop_condition=stop_condition,
            source_page=self.paths.now_dir / "next-action.md",
            reason="Codex selected this from the local wiki context and current state.",
        )

    def _read_optional(self, path: Path) -> str:
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def _collect_candidates(self) -> list[tuple[str, Path, dict[str, object]]]:
        candidates: list[tuple[str, Path, dict[str, object]]] = []
        for folder in (self.paths.projects_dir, self.paths.learning_dir, self.paths.now_dir):
            if not folder.exists():
                continue
            for page in folder.rglob("*.md"):
                metadata, body = parse_frontmatter(page.read_text(encoding="utf-8"))
                for action in re.findall(r"^- \[ \] (.+)$", body, flags=re.MULTILINE):
                    candidates.append((action.strip(), page, metadata))
        return candidates

    def _score(self, candidate: tuple[str, Path, dict[str, object]], energy: str, available_minutes: int) -> int:
        action, source, metadata = candidate
        score = 0
        priority = str(metadata.get("priority", "medium"))
        required = str(metadata.get("energy_required", "medium"))
        if priority == "high":
            score += 20
        if required == energy:
            score += 15
        if energy == "low" and self._looks_small(action):
            score += 10
        if available_minutes <= 25 and self._looks_small(action):
            score += 5
        if "learning" in source.parts:
            score += 3
        return score

    def _looks_small(self, action: str) -> bool:
        small_words = ("rough", "outline", "summary", "five", "5", "quick", "small")
        return any(word in action.lower() for word in small_words)

    def _stop_condition_for(self, action: str) -> str:
        if "outline" in action.lower():
            return "A rough outline exists, even if it is incomplete."
        if "summary" in action.lower():
            return "Five useful bullets are written."
        return "One visible, useful increment is finished."

    def _reason_for(self, source: Path, metadata: dict[str, object], energy: str) -> str:
        page_type = metadata.get("type", "wiki page")
        return f"This came from an open action on a {page_type} page and matches {energy} energy."

    def _write_next_action(
        self,
        recommendation: Recommendation,
        energy: str,
        mental_state: str,
        at: str | None,
    ) -> None:
        timestamp = at or datetime.now().astimezone().isoformat(timespec="seconds")
        path = self.paths.now_dir / "next-action.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        metadata = {
            "type": "next-action",
            "status": "active",
            "created": timestamp[:10],
            "updated": timestamp[:10],
        }
        source = recommendation.source_page.relative_to(self.paths.root).as_posix()
        body = "\n".join(
            [
                "# Next Action",
                "",
                "## Current recommendation",
                "",
                f"Action: {recommendation.action}",
                "",
                f"Timebox: {recommendation.timebox_minutes} minutes",
                "",
                f"Stop condition: {recommendation.stop_condition}",
                "",
                f"Why this: {recommendation.reason}",
                "",
                f"Related page: {source}",
                "",
                f"Created at: {timestamp}",
                "",
                "## Current state inputs",
                "",
                f"Energy: {energy}",
                f"Mental state: {mental_state}",
                "",
                "## Status",
                "",
                "pending",
                "",
                "## Feedback",
                "",
                "## History",
                "",
            ]
        )
        path.write_text(dump_frontmatter(metadata, body), encoding="utf-8")
