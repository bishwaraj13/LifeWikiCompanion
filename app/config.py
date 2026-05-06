from __future__ import annotations

import os
import sys
from pathlib import Path


APP_DIR_NAME = "lifewiki-companion"
DATA_DIR_ENV = "LIFEWIKI_DATA_DIR"


def default_data_root(home: Path | None = None, platform: str | None = None) -> Path:
    home = home or Path.home()
    platform = platform or sys.platform

    if platform == "darwin":
        return home / "Library" / "Application Support" / APP_DIR_NAME
    if platform.startswith("win"):
        base = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
        return base / APP_DIR_NAME

    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        return Path(xdg_data_home) / APP_DIR_NAME
    return home / ".local" / "share" / APP_DIR_NAME


def resolve_data_root(explicit_root: str | None) -> Path:
    if explicit_root:
        return Path(explicit_root).expanduser().resolve()

    env_root = os.environ.get(DATA_DIR_ENV)
    if env_root:
        return Path(env_root).expanduser().resolve()

    return default_data_root().expanduser().resolve()
