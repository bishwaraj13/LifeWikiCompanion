from __future__ import annotations

from typing import Any


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text

    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text

    raw = text[4:end]
    body = text[end + len("\n---\n") :]
    metadata: dict[str, Any] = {}
    current_key: str | None = None

    for line in raw.splitlines():
        if not line.strip():
            continue
        if line.startswith("  - ") and current_key:
            metadata.setdefault(current_key, []).append(_parse_scalar(line[4:]))
            continue
        key, _, value = line.partition(":")
        current_key = key.strip()
        value = value.strip()
        if value == "[]":
            metadata[current_key] = []
        elif value:
            metadata[current_key] = _parse_scalar(value)
        else:
            metadata[current_key] = []

    return metadata, body


def dump_frontmatter(metadata: dict[str, Any], body: str) -> str:
    lines = ["---"]
    for key, value in metadata.items():
        if isinstance(value, list):
            if value:
                lines.append(f"{key}:")
                lines.extend(f"  - {item}" for item in value)
            else:
                lines.append(f"{key}: []")
        elif value is None:
            lines.append(f"{key}:")
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines) + "\n" + body


def _parse_scalar(value: str) -> Any:
    if value in {"true", "false"}:
        return value == "true"
    return value
