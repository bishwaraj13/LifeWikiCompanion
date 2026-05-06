from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path

from app.wiki_engine.paths import LifeWikiPaths


@dataclass(frozen=True)
class CaptureResult:
    raw_markdown_path: Path
    jsonl_path: Path


class CaptureService:
    def __init__(self, paths: LifeWikiPaths):
        self.paths = paths
        self.paths.ensure_base_dirs()

    def capture_telegram_message(self, message: str, at: str | None = None) -> CaptureResult:
        timestamp = at or datetime.now().astimezone().isoformat(timespec="seconds")
        date = timestamp[:10]
        capture_path = self.paths.telegram_captures_dir / f"{date}.md"
        capture_path.parent.mkdir(parents=True, exist_ok=True)

        entry = f"\n## {timestamp}\n\n{message.rstrip()}\n"
        with capture_path.open("a", encoding="utf-8") as file:
            if capture_path.stat().st_size == 0:
                file.write(f"# Telegram captures for {date}\n")
            file.write(entry)

        self.paths.telegram_messages_jsonl.parent.mkdir(parents=True, exist_ok=True)
        record = {"source": "telegram", "captured_at": timestamp, "message": message}
        with self.paths.telegram_messages_jsonl.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=True) + "\n")

        return CaptureResult(capture_path, self.paths.telegram_messages_jsonl)
