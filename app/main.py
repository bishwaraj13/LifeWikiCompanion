from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

from app.config import resolve_data_root
from app.codex_bridge.runner import CodexRunner
from app.services.companion_service import CompanionService
from app.services.capture_service import CaptureService
from app.services.learning_service import LearningService
from app.services.maintenance_loop import run_maintenance_loop
from app.services.maintenance_service import MaintenanceService
from app.services.now_service import NowService
from app.services.setup_service import SetupRequiredError, SetupService
from app.services.source_ingest_service import SourceIngestService
from app.wiki_engine.paths import LifeWikiPaths


def main() -> None:
    parser = argparse.ArgumentParser(prog="lifewiki")
    parser.add_argument("--data-root", help="LifeWiki data directory. Defaults to LIFEWIKI_DATA_DIR or the OS data dir.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    setup = subparsers.add_parser("setup", help="Create first-run local config before interactions")
    setup.add_argument("--user-name", required=True)
    setup.add_argument("--telegram-user-id", default="")
    setup.add_argument("--codex-command", default="")

    subparsers.add_parser("status", help="Show setup and backend status")

    capture = subparsers.add_parser("capture", help="Preserve a raw Telegram-style capture")
    capture.add_argument("message")

    talk = subparsers.add_parser("talk", help="Reflect with the companion and update life context")
    talk.add_argument("message")

    lecture = subparsers.add_parser("lecture", help="Ingest manual lecture notes")
    lecture.add_argument("--title", required=True)
    lecture.add_argument("--topic", required=True)
    lecture.add_argument("--notes", required=True)
    lecture.add_argument("--watched-on")
    lecture.add_argument("--learning", nargs="*", default=[])
    lecture.add_argument("--project", nargs="*", default=[])
    lecture.add_argument("--source-url", default="")

    document = subparsers.add_parser("document", help="Ingest a local document into raw files and source notes")
    document.add_argument("path")
    document.add_argument("--title")

    webpage = subparsers.add_parser("webpage", help="Ingest a webpage into raw web clips and source notes")
    webpage.add_argument("url")
    webpage.add_argument("--title")

    now = subparsers.add_parser("now", help="Recommend exactly one useful next action")
    now.add_argument("--energy", default="medium")
    now.add_argument("--minutes", type=int, default=20)
    now.add_argument("--mental-state", default="")

    maintain = subparsers.add_parser("maintain", help="Ask Codex to review new raw input and maintain wiki pages")
    maintain.add_argument("--force", action="store_true", help="Run even when no raw files changed since the last checkpoint")
    maintain.add_argument("--watch", action="store_true", help="Keep running maintenance periodically")
    maintain.add_argument("--interval-seconds", type=int, default=3600, help="Seconds between maintenance runs in watch mode")

    args = parser.parse_args()
    paths = LifeWikiPaths(resolve_data_root(args.data_root))
    setup_service = SetupService(paths)

    if args.command == "setup":
        profile = setup_service.setup(
            user_name=args.user_name,
            telegram_user_id=args.telegram_user_id,
            codex_command=args.codex_command,
        )
        print(f"LifeWiki Companion is set up for {profile.user_name}.")
        print(f"Data root: {paths.root}")
        print(f"LLM backend: {profile.llm_backend}")
        if profile.codex_command:
            print(f"Codex command: {profile.codex_command}")
        else:
            print("Codex command: not found")
        return

    if args.command == "status":
        profile = setup_service.load_profile()
        if not profile:
            print("LifeWiki Companion is not set up yet.")
            print(f"Data root: {paths.root}")
            print("Run: lifewiki setup --user-name <name>")
            return
        print(f"User: {profile.user_name}")
        print(f"Data root: {paths.root}")
        print(f"LLM backend: {profile.llm_backend}")
        print(f"Codex command: {profile.codex_command or 'not found'}")
        print(f"Telegram user id: {profile.telegram_user_id or 'not configured'}")
        return

    try:
        profile = setup_service.require_setup()
    except SetupRequiredError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(2) from error

    if args.command == "capture":
        result = CaptureService(paths).capture_telegram_message(args.message)
        print(result.raw_markdown_path)
    elif args.command == "talk":
        response = CompanionService(paths, runner=CodexRunner(profile, paths.root)).reflect(args.message)
        print(response.text)
    elif args.command == "lecture":
        result = LearningService(paths).ingest_lecture_notes(
            title=args.title,
            topic=args.topic,
            notes=args.notes,
            watched_on=args.watched_on,
            related_learning=args.learning,
            related_projects=args.project,
            source_url=args.source_url,
        )
        print(result.lecture_page_path)
    elif args.command == "document":
        result = SourceIngestService(paths).ingest_document(Path(args.path), title=args.title)
        print(result.note_path)
    elif args.command == "webpage":
        result = SourceIngestService(paths).ingest_webpage(args.url, title=args.title)
        print(result.note_path)
    elif args.command == "now":
        recommendation = NowService(paths, runner=CodexRunner(profile, paths.root)).recommend_now(
            energy=args.energy,
            available_minutes=args.minutes,
            mental_state=args.mental_state,
        )
        print(f"Do this one thing now: {recommendation.action}")
        print(f"Timebox: {recommendation.timebox_minutes} minutes")
        print(f"Stop when: {recommendation.stop_condition}")
    elif args.command == "maintain":
        runner = CodexRunner(profile, paths.root)
        service = MaintenanceService(paths, runner)

        def maintain_once() -> None:
            result = service.maintain(force=args.force)
            if result.ran_codex:
                print(f"Maintained wiki from {len(result.raw_files_considered)} raw file(s).")
                print(result.checkpoint_path)
            else:
                print("No raw changes to maintain.")

        if args.watch:
            run_maintenance_loop(maintain_once, args.interval_seconds, time.sleep)
        else:
            maintain_once()


if __name__ == "__main__":
    main()
