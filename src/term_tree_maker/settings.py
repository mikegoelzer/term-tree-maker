"""
Constants for the term-tree-maker package.
"""
from __future__ import annotations

import os
from pathlib import Path

from platformdirs import user_log_dir

APP_NAME = "term-tree-maker"
APP_AUTHOR = "mikegoelzer"
ENV_LOG_PATH_VAR = "TERM_TREE_MAKER_LOG_PATH"

def _default_log_file() -> Path:
    """
    Platform-appropriate per-user log file, using platformdirs.user_log_dir().
    """
    # user_log_dir returns a str; wrap it in Path
    log_dir = Path(user_log_dir(APP_NAME, APP_AUTHOR))
    return log_dir / f"{APP_NAME}.log"


def _env_log_file() -> Path | None:
    """
    Optional override from $TERM_TREE_MAKER_LOG_PATH.
    """
    raw = os.getenv(ENV_LOG_PATH_VAR)
    if not raw:
        return None
    return Path(raw).expanduser()


def resolve_log_file() -> Path:
    """
    Final resolved log file path:
    1. $TERM_TREE_MAKER_LOG_PATH if set
    2. Otherwise platformdirs-based default.
    """
    env_path = _env_log_file()
    if env_path is not None:
        return env_path
    return _default_log_file()


#: The log file path to use for logging configuration.
LOG_FILE: Path = resolve_log_file()


def ensure_log_dir_exists() -> None:
    """
    Create the parent directory for LOG_FILE if it doesn't exist.
    Safe to call at import or before configuring logging.
    """
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)