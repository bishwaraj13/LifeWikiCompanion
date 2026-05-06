from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import shutil

from app.wiki_engine.paths import LifeWikiPaths


class SetupRequiredError(RuntimeError):
    pass


@dataclass(frozen=True)
class SetupProfile:
    user_name: str
    telegram_user_id: str
    llm_backend: str
    codex_command: str
    created_at: str


class SetupService:
    def __init__(self, paths: LifeWikiPaths):
        self.paths = paths

    def setup(
        self,
        user_name: str,
        telegram_user_id: str = "",
        codex_command: str = "",
    ) -> SetupProfile:
        self.paths.ensure_base_dirs()
        resolved_codex = codex_command or shutil.which("codex") or ""
        profile = SetupProfile(
            user_name=user_name,
            telegram_user_id=telegram_user_id,
            llm_backend="codex-cli" if resolved_codex else "none",
            codex_command=resolved_codex,
            created_at=datetime.now().astimezone().isoformat(timespec="seconds"),
        )
        self.paths.config_path.write_text(json.dumps(profile.__dict__, indent=2), encoding="utf-8")
        self._write_setup_readme(profile)
        return profile

    def load_profile(self) -> SetupProfile | None:
        if not self.paths.config_path.exists():
            return None
        data = json.loads(self.paths.config_path.read_text(encoding="utf-8"))
        return SetupProfile(
            user_name=str(data.get("user_name", "")),
            telegram_user_id=str(data.get("telegram_user_id", "")),
            llm_backend=str(data.get("llm_backend", "none")),
            codex_command=str(data.get("codex_command", "")),
            created_at=str(data.get("created_at", "")),
        )

    def require_setup(self) -> SetupProfile:
        profile = self.load_profile()
        if not profile:
            raise SetupRequiredError("Run `lifewiki setup --user-name <name>` before interacting.")
        return profile

    def is_telegram_user_allowed(self, telegram_user_id: str) -> bool:
        profile = self.load_profile()
        if not profile:
            return False
        if not profile.telegram_user_id:
            return False
        return profile.telegram_user_id == telegram_user_id

    def _write_setup_readme(self, profile: SetupProfile) -> Path:
        path = self.paths.system_dir / "README.md"
        codex_line = (
            f"Codex CLI: `{profile.codex_command}`"
            if profile.codex_command
            else "Codex CLI: not found yet. Install and authenticate Codex separately, then rerun setup."
        )
        path.write_text(
            "\n".join(
                [
                    "# LifeWiki Companion Data Directory",
                    "",
                    "This directory contains private runtime data for LifeWiki Companion.",
                    "",
                    f"User: {profile.user_name}",
                    codex_line,
                    "",
                    "Do not commit this directory into the code repository.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return path
