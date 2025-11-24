from __future__ import annotations

import sys
from typing import Optional

from . import init_logging
from .term_tree_maker import log, main as _cli_main


def main() -> int:
    """
    Console-script entry point. Ensures logging is configured before running
    the CLI implementation housed in ``term_tree_maker.py``.
    """
    init_logging()
    try:
        result: Optional[int] = _cli_main()
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 0
    except Exception as exc:
        log.exception("Error: %s", exc)
        return 1
    return result if isinstance(result, int) else 0


if __name__ == "__main__":
    sys.exit(main())
