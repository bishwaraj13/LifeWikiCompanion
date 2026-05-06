# LifeWiki Companion Agent Rules

This project treats the local Markdown wiki as the durable product.

## Core Rules

- Preserve original user input under `raw/`.
- Do not rewrite historical raw captures.
- Edit `wiki/` pages to maintain distilled, linked knowledge.
- Follow templates and prompts under `schema/` before creating new page types.
- Prefer Obsidian-compatible Markdown, YAML frontmatter, and `[[wikilinks]]`.
- `/now` must return exactly one useful action, not a task list.
- Prefer `uv run lifewiki ...` for runtime commands.

## LifeWiki Companion Mode

When the user is clearly using Codex as the LifeWiki companion, Codex should be the interface and run the harness commands on the user's behalf.

- Do not make the user manually translate plain conversation into CLI commands.
- For reflective personal conversation, run `uv run lifewiki talk "<message>"`.
- For quick raw notes, reminders, or ideas the user wants saved, run `uv run lifewiki capture "<message>"`.
- For `/now` or "what should I do now", run `uv run lifewiki now` with any supplied energy/time/context.
- For wiki distillation, run `uv run lifewiki maintain`.
- For periodic local maintenance, use `uv run lifewiki maintain --watch --interval-seconds <seconds>`.
- Do not capture ordinary software-development requests into `raw/` unless the user explicitly asks to save them to the LifeWiki.

## TDD Loop

Before adding behavior:

1. Write or update a focused test in `app/tests/`.
2. Run `uv run python -m unittest discover -s app/tests -v` and see it fail for the expected reason.
3. Implement the smallest useful change.
4. Run the suite again and keep it green.
