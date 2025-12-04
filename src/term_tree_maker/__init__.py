"""
term-tree-maker package.

Currently exposes the core tree-rendering script logic from ``tree.py`` and
console entrypoints defined in the package's ``cli`` modules.
"""

import logging
from curvpyutils.logging import configure_rich_root_logger, LoggingLevels
from curvpyutils.version_utils import get_version_str
import sys
from .settings import LOG_FILE, ensure_log_dir_exists

def init_logging() -> None:
    """
    Initialize logging for the term-tree-maker package.
    """
    try:
        ensure_log_dir_exists()
        configure_rich_root_logger(
            verbosity=LoggingLevels(
                stderr_level=logging.CRITICAL, 
                file_level=logging.DEBUG
            ), 
            log_file_path=LOG_FILE
        )
    except Exception as e:
        print(f"WARNING: could not configure rich root logger (curvpyutils version {get_version_str(short_version=True)}): {e}", file=sys.stderr)
        raise SystemExit(1)

init_logging()