from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from app.wiki_engine.frontmatter import dump_frontmatter
from app.wiki_engine.paths import LifeWikiPaths
from app.wiki_engine.wikilinks import slugify_title, wikilink


@dataclass(frozen=True)
class LectureIngestResult:
    raw_note_path: Path
    lecture_page_path: Path
    learning_page_paths: list[Path]


class LearningService:
    def __init__(self, paths: LifeWikiPaths):
        self.paths = paths
        self.paths.ensure_base_dirs()

    def ingest_lecture_notes(
        self,
        title: str,
        topic: str,
        notes: str,
        watched_on: str | None = None,
        related_learning: list[str] | None = None,
        related_projects: list[str] | None = None,
        source_url: str = "",
    ) -> LectureIngestResult:
        watched_on = watched_on or date.today().isoformat()
        related_learning = related_learning or []
        related_projects = related_projects or []
        slug = slugify_title(title)
        topic_slug = slugify_title(topic)

        raw_note = self.paths.lecture_notes_dir / f"{watched_on}-{slug}.md"
        raw_note.parent.mkdir(parents=True, exist_ok=True)
        raw_note.write_text(f"# {title}\n\nWatched on: {watched_on}\n\n{notes.rstrip()}\n", encoding="utf-8")

        lecture_page = self.paths.lectures_dir / topic_slug / f"{watched_on}-{slug}.md"
        lecture_page.parent.mkdir(parents=True, exist_ok=True)
        raw_reference = raw_note.relative_to(self.paths.root).as_posix()
        body = self._lecture_body(title, raw_reference, notes, related_learning, related_projects)
        metadata = {
            "type": "lecture-note",
            "status": "processed",
            "topic": topic,
            "lecture_title": title,
            "source_type": "manual",
            "source_url": source_url,
            "watched_on": watched_on,
            "created": date.today().isoformat(),
            "updated": date.today().isoformat(),
            "tags": ["lecture", topic_slug],
            "related_learning": [wikilink(item) for item in related_learning],
            "related_projects": [wikilink(item) for item in related_projects],
            "confidence": "medium",
        }
        lecture_page.write_text(dump_frontmatter(metadata, body), encoding="utf-8")

        learning_pages = [self._ensure_learning_topic(topic_name, lecture_page) for topic_name in related_learning]
        return LectureIngestResult(raw_note, lecture_page, learning_pages)

    def _ensure_learning_topic(self, topic_name: str, lecture_page: Path) -> Path:
        path = self.paths.learning_dir / f"{slugify_title(topic_name)}.md"
        if path.exists():
            return path

        metadata = {
            "type": "learning-topic",
            "status": "active",
            "level": "beginner",
            "target_level": "practical",
            "created": date.today().isoformat(),
            "updated": date.today().isoformat(),
            "tags": ["learning", slugify_title(topic_name)],
            "related_projects": [],
            "related_lectures": [wikilink(lecture_page.stem)],
        }
        body = "\n".join(
            [
                f"# {topic_name}",
                "",
                "## Why I am learning this",
                "",
                "## Current understanding",
                "",
                "## Key concepts",
                "",
                "## Confusions / gaps",
                "",
                "## Examples",
                "",
                "## Related projects",
                "",
                "- [[]]",
                "",
                "## Related lectures",
                "",
                f"- {wikilink(lecture_page.stem)}",
                "",
                "## Practice tasks",
                "",
                "- [ ] Write a small example that uses this concept.",
                "",
                "## Next study action",
                "",
                "Write a five-bullet summary of what I understand so far.",
                "",
                "## Source log",
                "",
            ]
        )
        path.write_text(dump_frontmatter(metadata, body), encoding="utf-8")
        return path

    def _lecture_body(
        self,
        title: str,
        raw_reference: str,
        notes: str,
        related_learning: list[str],
        related_projects: list[str],
    ) -> str:
        learning_links = "\n".join(f"- {wikilink(item)}" for item in related_learning) or "- [[]]"
        project_links = "\n".join(f"- {wikilink(item)}" for item in related_projects) or "- [[]]"
        return "\n".join(
            [
                f"# {title}",
                "",
                "## Source",
                "",
                "Manual lecture notes",
                "",
                "## Why I watched this",
                "",
                "## Raw note reference",
                "",
                f"- {raw_reference}",
                "",
                "## Summary",
                "",
                notes.strip(),
                "",
                "## Key ideas",
                "",
                "## Concepts explained",
                "",
                learning_links,
                "",
                "## Things I understood",
                "",
                "## Things still confusing",
                "",
                "## Important examples",
                "",
                "## Commands / code snippets",
                "",
                "## Project relevance",
                "",
                project_links,
                "",
                "## Follow-up questions",
                "",
                "## Action items",
                "",
                "- [ ] Write a rough summary in the related learning page.",
                "",
                "## Links created",
                "",
                learning_links,
                project_links,
                "",
            ]
        )
