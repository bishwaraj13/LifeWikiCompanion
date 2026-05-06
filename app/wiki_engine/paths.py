from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LifeWikiPaths:
    root: Path

    @property
    def raw_dir(self) -> Path:
        return self.root / "raw"

    @property
    def wiki_dir(self) -> Path:
        return self.root / "wiki"

    @property
    def telegram_captures_dir(self) -> Path:
        return self.raw_dir / "telegram" / "captures"

    @property
    def telegram_messages_jsonl(self) -> Path:
        return self.raw_dir / "telegram" / "messages.jsonl"

    @property
    def lecture_notes_dir(self) -> Path:
        return self.raw_dir / "lectures" / "notes"

    @property
    def files_dir(self) -> Path:
        return self.raw_dir / "files"

    @property
    def web_clips_dir(self) -> Path:
        return self.raw_dir / "web_clips"

    @property
    def companion_conversations_dir(self) -> Path:
        return self.raw_dir / "companion" / "conversations"

    @property
    def learning_dir(self) -> Path:
        return self.wiki_dir / "learning"

    @property
    def lectures_dir(self) -> Path:
        return self.wiki_dir / "lectures"

    @property
    def projects_dir(self) -> Path:
        return self.wiki_dir / "projects"

    @property
    def now_dir(self) -> Path:
        return self.wiki_dir / "now"

    @property
    def sources_dir(self) -> Path:
        return self.wiki_dir / "sources"

    @property
    def system_dir(self) -> Path:
        return self.root / "system"

    @property
    def config_path(self) -> Path:
        return self.system_dir / "config.json"

    @property
    def self_dir(self) -> Path:
        return self.wiki_dir / "self"

    @property
    def reviews_dir(self) -> Path:
        return self.wiki_dir / "reviews"

    def ensure_base_dirs(self) -> None:
        for path in (
            self.telegram_captures_dir,
            self.lecture_notes_dir,
            self.files_dir,
            self.web_clips_dir,
            self.companion_conversations_dir,
            self.learning_dir,
            self.lectures_dir,
            self.projects_dir,
            self.now_dir,
            self.sources_dir,
            self.self_dir,
            self.reviews_dir,
            self.system_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)
