"""
Constants for the term-tree-maker package.
"""
from __future__ import annotations

import os
from pathlib import Path

from platformdirs import user_log_dir
from logging import getLogger

log = getLogger(__name__)

TERM_TREE_MAKER_ENV_VAR_PREFIX = "TERM_TREE_MAKER_" # prefix for environment variables
APP_NAME                       = "term-tree-maker"
APP_AUTHOR                     = "mikegoelzer"
ENV_LOG_PATH_VAR               = f"{TERM_TREE_MAKER_ENV_VAR_PREFIX}LOG_PATH"
DEFAULT_LOG_FILE_WIDTH         = 120                        # width of the log file
LOG_FILE_WIDTH_BUFFER          = 40                         # buffer needed for the log file to not wrap

def resolve_log_file() -> Path:
    """
    Final resolved, absolute log file path:
    1. $TERM_TREE_MAKER_LOG_PATH if set
    2. Otherwise platformdirs-based default.
    """
    #
    # Helper functions for resolving the log file path:
    #
    def _get_default_log_file_path() -> Path:
        """
        Platform-appropriate per-user log file, using platformdirs.user_log_dir().
        """
        # user_log_dir returns a str; wrap it in Path
        log_dir = Path(user_log_dir(APP_NAME, APP_AUTHOR))
        return log_dir / f"{APP_NAME}.log"

    def _get_env_log_file_path() -> Path | None:
        """
        Optional override from $TERM_TREE_MAKER_LOG_PATH.
        """
        raw = os.getenv(ENV_LOG_PATH_VAR)
        if raw is None:
            return None
        raw_path = Path(raw).expanduser()
        return raw_path

    #
    # Main logic:
    #
    ret = None
    env_path = _get_env_log_file_path()
    if env_path is not None:
        ret = env_path
    else:
        ret = _get_default_log_file_path()
    try:
        return ret.resolve()
    except Exception as e:
        print(f"ERROR: could not resolve log file path: {e}", file=sys.stderr)
        raise SystemExit(1) from e

# The log file path to use for logging configuration.
LOG_FILE: Path = resolve_log_file()


def ensure_log_dir_exists() -> None:
    """
    Create the parent directory for LOG_FILE if it doesn't exist.
    Safe to call at import or before configuring logging.
    """
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


###############################################################################
# Environment variable constants used in python and shell script
###############################################################################

DEFAULT_EXTRA_LINES              = 1
DEFAULT_COLS                     = 120
DEFAULT_CHUNK_LINES_AMOUNT       = 50
DEFAULT_DEBUG_PRESERVE_TMP_FILES = 0 # 1 to preserve, 0 to delete

def get_env_or_defaults() -> dict[str, int | str]:
    """
    Get the TERM_TREE_MAKER_* environment variables or their default values.
    """
    defaults = {
        f"{TERM_TREE_MAKER_ENV_VAR_PREFIX}EXTRA_LINES":              DEFAULT_EXTRA_LINES,
        f"{TERM_TREE_MAKER_ENV_VAR_PREFIX}COLS":                     DEFAULT_COLS,
        f"{TERM_TREE_MAKER_ENV_VAR_PREFIX}CHUNK_LINES_AMOUNT":       DEFAULT_CHUNK_LINES_AMOUNT,
        f"{TERM_TREE_MAKER_ENV_VAR_PREFIX}DEBUG_PRESERVE_TMP_FILES": DEFAULT_DEBUG_PRESERVE_TMP_FILES,
    }
    ret = {}
    log_lines: list[str] = ["Found environment variables:"]
    initial_len_log_lines = len(log_lines)
    longest_key = max(map(len, {**os.environ, **defaults}.keys()))
    for key, value in os.environ.items():
        if key.startswith(TERM_TREE_MAKER_ENV_VAR_PREFIX):
            new_value = int(value) if isinstance(value, str) and value.isdigit() else value
            new_value_str = f"{new_value}" if isinstance(new_value, int) else f"'{new_value}'"
            log_lines.append(f"  {key.ljust(longest_key)} = {new_value_str}")
            ret[key] = new_value
    if len(log_lines) == initial_len_log_lines:
        log_lines.append("  (none)")
    
    # set these values in the environment so shell scripts can use them
    log_lines.append("Setting previously unset env vars using default values:")
    initial_len_log_lines = len(log_lines)
    for key, value in defaults.items():
        if key not in ret:
            new_value = int(value) if isinstance(value, str) and value.isdigit() else value
            new_value_str = f"{new_value}" if isinstance(new_value, int) else f"'{new_value}'"
            ret[key] = new_value
            os.environ[key] = str(new_value)
            log_lines.append(f"  {key.ljust(longest_key)} = {new_value_str}")
    if len(log_lines) == initial_len_log_lines:
        log_lines.append("  (none)")
    
    for line in log_lines:
        log.info(line)
    
    return ret