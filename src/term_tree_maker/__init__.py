"""
term-tree-maker package.

Currently exposes the core tree-rendering script logic from ``tree.py`` and
console entrypoints defined in the package's ``cli`` modules.
"""

import logging
from curvpyutils.logging import configure_rich_root_logger, LoggingLevels
from curvpyutils.version_utils import get_version_str
from typing import Optional
import sys
from .settings import LOG_FILE, DEFAULT_LOG_FILE_WIDTH
import logging

log = logging.getLogger(__name__)

_init_logging_done = False

def init_logging(force_reinit: bool = False, log_file_width: Optional[int] = None) -> None:
    """
    Initialize logging for the term-tree-maker package.
    """
    global _init_logging_done
    if _init_logging_done and not force_reinit:
        return

    try:
        if LOG_FILE is None:
            raise FileNotFoundError(f"LOG_FILE is not set")
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        kwargs = {}
        if log_file_width is not None:
            kwargs["log_file_width"] = log_file_width
        else:
            kwargs["log_file_width"] = DEFAULT_LOG_FILE_WIDTH
        configure_rich_root_logger(
            verbosity=LoggingLevels(
                stderr_level=logging.CRITICAL, 
                file_level=logging.DEBUG
            ), 
            log_file_path=LOG_FILE,
            **kwargs
        )
    except Exception as e:
        print(f"ERROR: could not configure rich root logger (curvpyutils version {get_version_str(short_version=True)}): {e}", file=sys.stderr)
        raise SystemExit(1) from e
    
    if not _init_logging_done:
        log.info(f"Starting up with log file {LOG_FILE} and width {log_file_width}")
    else:
        log.info(f"Re-initializing with log file {LOG_FILE} and width {log_file_width}")
    
    _init_logging_done = True
