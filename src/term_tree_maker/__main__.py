from __future__ import annotations

import sys
from typing import Optional

from . import init_logging
from .term_tree_maker import log, main as _cli_main
import argparse
from curvpyutils.shellutils import get_console_width
from .settings import DEFAULT_LOG_FILE_WIDTH, LOG_FILE_WIDTH_BUFFER

def parse_args() -> tuple[argparse.Namespace, argparse.ArgumentParser]:
    parent_parser = argparse.ArgumentParser(add_help=False)
    display_group = parent_parser.add_argument_group("Display Options")
    display_group.add_argument(
        "--width", '-w', 
        type=int, 
        default=min(get_console_width(), DEFAULT_LOG_FILE_WIDTH), 
        help="Max width of tree; if not specified, the terminal's width minus a buffer "
             "needed for the log file to be viewable is used (default: %(default)s).")
    args, _ = parent_parser.parse_known_args() # ignore unknown arguments
    return args, parent_parser

def main() -> int:
    """
    Console-script entry point. Ensures logging is configured before running
    the CLI implementation housed in ``term_tree_maker.py``.
    """
    args, parent_parser = parse_args()
    init_logging(log_file_width=args.width+LOG_FILE_WIDTH_BUFFER)
    try:
        result: Optional[int] = _cli_main(parent_parser=parent_parser)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 0
    except Exception as exc:
        log.exception("Error: %s", exc)
        return 1
    return result if isinstance(result, int) else 0


if __name__ == "__main__":
    sys.exit(main())
