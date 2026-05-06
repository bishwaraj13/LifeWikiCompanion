from pathlib import Path
import re


def slugify_title(title: str) -> str:
    slug = title.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def wikilink(title: str) -> str:
    return f"[[{title}]]"


def wikilink_target(link: str, known_pages: dict[str, Path]) -> Path | None:
    title = link.strip()
    if title.startswith("[[") and title.endswith("]]"):
        title = title[2:-2]
    return known_pages.get(slugify_title(title))
