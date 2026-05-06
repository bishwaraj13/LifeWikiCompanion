from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
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
class MaintenanceResult:
    ran_codex: bool
    raw_files_considered: list[str]
    checkpoint_path: Path
    codex_result: CodexRunResult | None = None


class MaintenanceService:
    def __init__(self, paths: LifeWikiPaths, runner: CodexPromptRunner, repo_root: Path | None = None):
        self.paths = paths
        self.runner = runner
        self.repo_root = repo_root or Path(__file__).resolve().parents[2]
        self.paths.ensure_base_dirs()

    def maintain(self, at: str | None = None, force: bool = False) -> MaintenanceResult:
        timestamp = at or datetime.now().astimezone().isoformat(timespec="seconds")
        before = self._raw_fingerprints()
        previous = self._load_checkpoint()
        changed = self._changed_raw_files(before, previous)
        if not changed and not force:
            return MaintenanceResult(False, [], self._checkpoint_path())

        if not self.runner.is_available():
            raise RuntimeError("Codex CLI is not configured. Run setup after installing and authenticating Codex.")

        considered = changed or sorted(before)
        prompt = self._build_prompt(considered, timestamp)
        codex_result = self.runner.run_prompt(prompt, timeout_seconds=300)

        after = self._raw_fingerprints()
        if before != after:
            raise RuntimeError("Codex maintenance changed files under raw/. Refusing to checkpoint this run.")
        if codex_result.returncode != 0:
            raise RuntimeError(f"Codex maintenance failed: {codex_result.stderr.strip() or codex_result.stdout.strip()}")

        self._write_checkpoint(timestamp, after)
        return MaintenanceResult(True, considered, self._checkpoint_path(), codex_result)

    def _checkpoint_path(self) -> Path:
        return self.paths.system_dir / "maintenance-state.json"

    def _load_checkpoint(self) -> dict[str, dict[str, str | int]]:
        path = self._checkpoint_path()
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        raw_files = data.get("raw_files", {})
        if not isinstance(raw_files, dict):
            return {}
        return raw_files

    def _write_checkpoint(self, timestamp: str, raw_files: dict[str, dict[str, str | int]]) -> None:
        path = self._checkpoint_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "last_maintained_at": timestamp,
            "raw_files": raw_files,
        }
        path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    def _raw_fingerprints(self) -> dict[str, dict[str, str | int]]:
        if not self.paths.raw_dir.exists():
            return {}
        fingerprints = {}
        for path in sorted(item for item in self.paths.raw_dir.rglob("*") if item.is_file()):
            relative = path.relative_to(self.paths.root).as_posix()
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            stat = path.stat()
            fingerprints[relative] = {
                "sha256": digest,
                "size": stat.st_size,
            }
        return fingerprints

    def _changed_raw_files(
        self,
        current: dict[str, dict[str, str | int]],
        previous: dict[str, dict[str, str | int]],
    ) -> list[str]:
        changed = []
        for relative, fingerprint in sorted(current.items()):
            if previous.get(relative) != fingerprint:
                changed.append(relative)
        return changed

    def _build_prompt(self, raw_files: list[str], timestamp: str) -> str:
        sections = [
            "# LifeWiki Maintenance Run",
            "",
            f"Timestamp: {timestamp}",
            "",
            "You are Codex maintaining the user's local Markdown wiki.",
            "",
            "## Repository Rules",
            "",
            self._read_optional(self.repo_root / "AGENTS.md").strip(),
            "",
            "## Companion Reflection Prompt",
            "",
            self._read_optional(self.repo_root / "schema/prompts/companion_reflection.md").strip(),
            "",
            "## Recommend Now Prompt",
            "",
            self._read_optional(self.repo_root / "schema/prompts/recommend_now.md").strip(),
            "",
            "## Wiki Maintenance Prompt",
            "",
            self._read_optional(self.repo_root / "schema/prompts/wiki_maintenance.md").strip(),
            "",
            "## Page Templates",
            "",
            self._template_reference().strip(),
            "",
            "## Maintenance Task",
            "",
            "- Read the raw material listed below.",
            "- Preserve every file under `raw/` exactly as-is.",
            "- Edit only useful distilled Markdown pages under `wiki/`.",
            "- Use YAML frontmatter, Obsidian-compatible Markdown, and `[[wikilinks]]`.",
            "- Follow existing page templates under `schema/templates/` before creating new page types.",
            "- Prefer updating existing pages over creating duplicates.",
            "- Keep the result practical: capture patterns, projects, learning topics, sources, open loops, and daily review notes when useful.",
            "",
            "## Raw Files To Review",
            "",
        ]
        for relative in raw_files:
            sections.extend(
                [
                    f"### {relative}",
                    "",
                    "```text",
                    self._raw_excerpt(relative),
                    "```",
                    "",
                ]
            )
        return "\n".join(sections)

    def _read_optional(self, path: Path) -> str:
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def _template_reference(self) -> str:
        templates_dir = self.repo_root / "schema/templates"
        if not templates_dir.exists():
            return ""
        sections = []
        for path in sorted(templates_dir.glob("*.md")):
            sections.extend(
                [
                    f"### schema/templates/{path.name}",
                    "",
                    "```markdown",
                    path.read_text(encoding="utf-8").strip(),
                    "```",
                    "",
                ]
            )
        return "\n".join(sections)

    def _raw_excerpt(self, relative_path: str, max_chars: int = 6000) -> str:
        path = self.paths.root / relative_path
        text = path.read_text(encoding="utf-8", errors="replace")
        if len(text) <= max_chars:
            return text
        return text[-max_chars:]
