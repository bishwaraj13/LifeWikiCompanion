# LifeWiki Companion

Local-first companion for maintaining a personal Markdown wiki from raw thoughts, life reflections, source documents, lecture notes, projects, learning topics, and open loops.

The core idea:

```text
raw sources -> maintained Markdown wiki -> companion replies, review, and /now
```

This repository is only for code, schema, prompts, and tests. Your private `raw/`, `wiki/`, and `system/` data live in a separate data directory.

## Mental Model

There are three instruction layers:

```text
AGENTS.md
  Instructions for Codex when it works inside this repository.

schema/prompts/*.md
  Prompt files the app uses when asking Codex to behave as the LifeWiki companion.

README.md
  Human-facing setup and usage documentation.
```

`raw/` is append-only source material. `wiki/` is the living knowledge base. `schema/` is the constitution for page structure and companion behavior.

The Python code is intentionally a thin harness. It owns durable mechanics: setup, paths, raw preservation, source copying, timestamps, Codex invocation, checkpoints, and raw integrity checks. The reflective behavior belongs in `AGENTS.md` and `schema/prompts/*.md`, where Codex can interpret the wiki context directly.

## Current Status

Working now:

- first-run setup gate
- local CLI
- raw capture preservation
- Codex-powered `talk` command, with deterministic fallback when Codex is unavailable
- lecture note ingestion
- local document ingestion
- webpage ingestion
- PDF preservation, with optional text extraction
- Codex-powered `/now` recommendations, with deterministic fallback when Codex is unavailable
- Codex CLI detection
- Codex-powered wiki maintenance through `maintain`

Not wired yet:

- Telegram bot runtime
- real login/OAuth flow
- vector search
- SQLite persistence beyond local config
- review/lint jobs beyond Codex maintenance checkpoints

## Data Directory

By default, LifeWiki Companion stores private data outside this repo:

- `LIFEWIKI_DATA_DIR`, when set
- Linux: `~/.local/share/lifewiki-companion`
- macOS: `~/Library/Application Support/lifewiki-companion`
- Windows: `%LOCALAPPDATA%\lifewiki-companion`

Every command also accepts:

```bash
--data-root /path/to/lifewiki-data
```

Inside the data directory, the app creates:

```text
raw/      original captures, documents, PDFs, webpages
wiki/     maintained Markdown knowledge base
system/   local config and runtime state
```

Do not commit your data directory.

## Setup

Run setup before any interaction:

```bash
uv run lifewiki --data-root /tmp/lifewiki-data setup --user-name DemoUser
```

Check status:

```bash
uv run lifewiki --data-root /tmp/lifewiki-data status
```

Setup writes:

```text
system/config.json
```

Interactions such as `talk`, `capture`, `lecture`, `document`, `webpage`, and `now` require setup first.

## Codex

LifeWiki Companion is intended to work with Codex CLI as the local LLM/wiki maintainer.

Install and authenticate Codex CLI separately. LifeWiki Companion should not store Codex credentials. During setup, it records the `codex` command path if available.

Check Codex:

```bash
codex --version
```

If needed:

```bash
codex login
```

Codex-powered behavior is wired through:

```text
app/services/companion_service.py
  Preserves the raw conversation, builds a companion prompt, asks Codex to update useful wiki context, and returns Codex's reply.

app/services/now_service.py
  Builds a /now prompt from project, learning, and open action context, asks Codex for exactly one action, and writes wiki/now/next-action.md.

app/services/maintenance_service.py
  Reviews changed raw files, asks Codex to maintain wiki pages, verifies raw files were not changed, and records a checkpoint.
```

If Codex CLI is not configured, `talk` and `now` still return conservative deterministic fallback responses. `maintain` requires Codex because its whole job is wiki distillation.

## Usage

If you are already talking to Codex in this repository, you can use Codex as the interface. Say you want LifeWiki companion mode, then talk normally; the repo instructions tell Codex to run `uv run lifewiki talk`, `capture`, `now`, or `maintain` for you when that is clearly what you mean.

Talk to the companion:

```bash
uv run lifewiki --data-root /tmp/lifewiki-data talk "Turn scattered GenAI project notes into a clearer implementation plan."
```

This preserves the raw conversation, asks Codex to update useful distilled wiki pages, and returns a short companion reply. Depending on the message, Codex may update pages like:

```text
raw/companion/conversations/YYYY-MM-DD.md
wiki/projects/genai-research-assistant.md
wiki/learning/rag-evaluation.md
wiki/reviews/daily/YYYY-MM-DD.md
```

Capture a raw Telegram-style thought:

```bash
uv run lifewiki --data-root /tmp/lifewiki-data capture "Compare chunking strategies for a small RAG prototype and note where evaluation should happen."
```

Ingest lecture notes:

```bash
uv run lifewiki --data-root /tmp/lifewiki-data lecture \
  --title "RAG Evaluation Basics" \
  --topic "GenAI Systems" \
  --notes "Track retrieval quality separately from answer quality. Keep a small golden dataset for regression checks." \
  --learning "retrieval augmented generation" "LLM evaluation" \
  --project "GenAI Research Assistant"
```

Ingest a local document:

```bash
uv run lifewiki --data-root /tmp/lifewiki-data document ./notes/rag-evaluation.txt
```

Ingest a webpage:

```bash
uv run lifewiki --data-root /tmp/lifewiki-data webpage https://example.com/article
```

Ask for one next action:

```bash
uv run lifewiki --data-root /tmp/lifewiki-data now --energy medium --minutes 30 --mental-state focused
```

Ask Codex to review new raw input and maintain the wiki:

```bash
uv run lifewiki --data-root /tmp/lifewiki-data maintain
```

The command reviews raw files changed since the last checkpoint, asks Codex to update `wiki/`, verifies that `raw/` was not changed, and records:

```text
system/maintenance-state.json
```

Run even when there are no detected raw changes:

```bash
uv run lifewiki --data-root /tmp/lifewiki-data maintain --force
```

For periodic background maintenance, schedule the same command with cron or a user service. Example cron entry for every hour:

```cron
0 * * * * cd /path/to/LifeWikiCompanion && LIFEWIKI_DATA_DIR="$HOME/.local/share/lifewiki-companion" uv run lifewiki maintain
```

Or run the built-in loop in a terminal, service, or process manager:

```bash
uv run lifewiki maintain --watch --interval-seconds 3600
```

## PDF Support

PDF files are always preserved under:

```text
raw/files/
```

They also get a source note under:

```text
wiki/sources/
```

Text extraction uses the optional `pypdf` dependency:

```bash
uv run --extra pdf lifewiki document ./paper.pdf
```

Without `pypdf`, the raw PDF is still preserved and the source note explains that extraction is pending.

## Development

Run tests:

```bash
uv run python -m unittest discover -s app/tests -v
```

This project is being built test-first. Before adding behavior:

1. Add or update a focused test in `app/tests/`.
2. Run the suite and see it fail for the expected reason.
3. Implement the smallest useful change.
4. Run the suite again and keep it green.

Package entrypoint is defined in [pyproject.toml](pyproject.toml):

```bash
lifewiki
```

The intended installed usage is:

```bash
lifewiki setup --user-name DemoUser
lifewiki talk "Clarify the next step for a GenAI prototype."
lifewiki now --energy medium --minutes 30
```

## Files To Edit

Use these files for these purposes:

```text
AGENTS.md
  Repo-level Codex rules.

schema/prompts/companion_reflection.md
  Companion voice and reflection behavior.

schema/prompts/recommend_now.md
  Rules for choosing one next action.

schema/prompts/wiki_maintenance.md
  Rules for periodic Codex wiki maintenance.

schema/templates/*.md
  Page structure for wiki notes.
```

Do not put companion personality rules mainly in `README.md`; companion behavior belongs in `schema/prompts/`.

## Code Boundary

Keep Python boring. It should preserve inputs, route commands, assemble prompt context, run Codex, parse small structured outputs, and verify invariants. Avoid adding companion personality, rich ranking logic, or life interpretation directly to Python services unless it is only an offline fallback.

Put behavior changes here instead:

```text
AGENTS.md
  Repo-level rules and LifeWiki companion routing.

schema/prompts/companion_reflection.md
  How the companion should respond and what kind of wiki context to update.

schema/prompts/recommend_now.md
  How to choose exactly one useful next action.

schema/prompts/wiki_maintenance.md
  How to distill raw material into durable wiki pages.
```

## Common Confusions

- `AGENTS.md` is for Codex behavior in this repo.
- `schema/prompts/companion_reflection.md` is for companion personality.
- `raw/` is historical source material and should stay unchanged.
- `wiki/` is where distilled, linked notes evolve.
- The app repository and private data directory are separate on purpose.

## Next Steps

1. Add maintenance triggers after capture/source/lecture.
   The `maintain` command exists; next, add opt-in automatic maintenance after new input.

2. Add Telegram bot runtime.
   Implement bot token config, authenticated sender checks, command routing for `/now`, and normal-message routing to `CompanionService`.

3. Improve setup/login.
   Add interactive setup, Telegram user verification, config validation, and a clearer install flow.

4. Add source extraction depth.
   Improve webpage readability extraction, add PDF text extraction tests with `pypdf`, and support uploaded files from Telegram.

5. Add review and lint commands.
   Implement `review`, `weekly-review`, and `lint` flows for stale links, missing frontmatter, unresolved open loops, and neglected projects.

6. Add retrieval.
   Start with keyword search over Markdown, then add vector indexing once the wiki format stabilizes.

7. Add distribution.
   Make this install cleanly with `pipx`, document Codex CLI prerequisites, and add a simple `lifewiki doctor` command.

## Telegram Status

Telegram is not wired yet. The current services are ready for Telegram handlers:

- normal messages -> `CompanionService.reflect`
- `/now` -> `NowService.recommend_now`
- lecture/document/webpage uploads -> ingestion services

The next real product milestone is making Telegram the default interface.
