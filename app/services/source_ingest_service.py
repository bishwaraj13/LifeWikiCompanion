from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
import shutil
from urllib.request import Request, urlopen

from app.wiki_engine.frontmatter import dump_frontmatter
from app.wiki_engine.paths import LifeWikiPaths
from app.wiki_engine.wikilinks import slugify_title


@dataclass(frozen=True)
class SourceIngestResult:
    raw_path: Path
    note_path: Path
    title: str
    extracted_text: str


class SourceIngestService:
    def __init__(self, paths: LifeWikiPaths):
        self.paths = paths
        self.paths.ensure_base_dirs()

    def ingest_document(self, source_path: Path, title: str | None = None) -> SourceIngestResult:
        source_path = source_path.expanduser().resolve()
        if not source_path.exists():
            raise FileNotFoundError(source_path)

        raw_path = self.paths.files_dir / source_path.name
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, raw_path)

        resolved_title = title or source_path.stem.replace("-", " ").replace("_", " ").title()
        suffix = source_path.suffix.lower()
        if suffix == ".pdf":
            source_type = "pdf"
            extracted = self._extract_pdf_text(raw_path)
        elif suffix in {".md", ".markdown", ".txt"}:
            source_type = "document"
            extracted = raw_path.read_text(encoding="utf-8", errors="replace")
        else:
            source_type = "document"
            extracted = f"Raw file preserved. Add an extractor for `{suffix or 'unknown'}` files when needed."

        note_path = self._write_source_note(
            title=resolved_title,
            source_type=source_type,
            raw_path=raw_path,
            extracted_text=extracted,
        )
        return SourceIngestResult(raw_path, note_path, resolved_title, extracted)

    def ingest_webpage(
        self,
        url: str,
        html: str | None = None,
        title: str | None = None,
        captured_on: str | None = None,
    ) -> SourceIngestResult:
        captured_on = captured_on or date.today().isoformat()
        html = html if html is not None else self._fetch_webpage(url)
        parsed = _ReadableHtmlParser()
        parsed.feed(html)
        resolved_title = title or parsed.title or url.rstrip("/").rsplit("/", 1)[-1] or "webpage"
        slug = slugify_title(resolved_title)

        raw_path = self.paths.web_clips_dir / f"{captured_on}-{slug}.html"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(html, encoding="utf-8")

        extracted = parsed.readable_text()
        note_path = self._write_source_note(
            title=resolved_title,
            source_type="webpage",
            raw_path=raw_path,
            extracted_text=extracted,
            source_url=url,
        )
        return SourceIngestResult(raw_path, note_path, resolved_title, extracted)

    def _write_source_note(
        self,
        title: str,
        source_type: str,
        raw_path: Path,
        extracted_text: str,
        source_url: str = "",
    ) -> Path:
        slug = slugify_title(title)
        note_path = self.paths.sources_dir / f"{slug}.md"
        note_path.parent.mkdir(parents=True, exist_ok=True)
        raw_reference = raw_path.relative_to(self.paths.root).as_posix()
        today = date.today().isoformat()
        metadata = {
            "type": "source-note",
            "status": "captured",
            "source_type": source_type,
            "source_url": source_url,
            "created": today,
            "updated": today,
            "source": [raw_reference],
            "tags": ["source", source_type],
            "confidence": "medium",
        }
        body = "\n".join(
            [
                f"# {title}",
                "",
                "## Source",
                "",
                f"- {raw_reference}",
                "",
                "## Extracted text",
                "",
                extracted_text.strip() or "No text extracted yet.",
                "",
                "## Notes",
                "",
                "## Links to create",
                "",
                "- [[]]",
                "",
                "## Action items",
                "",
                "- [ ] Decide whether this source should update a project, learning topic, or synthesis page.",
                "",
            ]
        )
        note_path.write_text(dump_frontmatter(metadata, body), encoding="utf-8")
        return note_path

    def _fetch_webpage(self, url: str) -> str:
        request = Request(url, headers={"User-Agent": "LifeWikiCompanion/0.1"})
        with urlopen(request, timeout=20) as response:
            content_type = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(content_type, errors="replace")

    def _extract_pdf_text(self, raw_path: Path) -> str:
        try:
            from pypdf import PdfReader
        except ImportError:
            return "PDF text extraction requires the optional `pypdf` dependency. Raw PDF was preserved."

        reader = PdfReader(str(raw_path))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n\n".join(page.strip() for page in pages if page.strip())
        return text or "PDF text extraction found no readable text. Raw PDF was preserved."


class _ReadableHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self._in_title = False
        self._skip_depth = 0
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "title":
            self._in_title = True
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
        if tag in {"p", "h1", "h2", "h3", "li", "br"}:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        cleaned = " ".join(data.split())
        if not cleaned:
            return
        if self._in_title:
            self.title = cleaned
            return
        if not self._skip_depth:
            self._chunks.append(cleaned)

    def readable_text(self) -> str:
        lines = []
        for chunk in "\n".join(self._chunks).splitlines():
            cleaned = " ".join(chunk.split())
            if cleaned:
                lines.append(cleaned)
        return "\n".join(lines)
