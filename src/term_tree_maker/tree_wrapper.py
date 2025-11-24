import runpy
import sys
from pathlib import Path
import logging

log = logging.getLogger(__name__)

def main() -> None:
    """
    Console entrypoint for the ``tree`` command.

    This simply executes the original ``tree.py`` script inside the
    installed package, forwarding any command-line arguments.
    """
    try:
        package_dir = Path(__file__).resolve().parent
        script_path = package_dir / "tree.py"

        # Emulate ``python tree.py ...`` semantics
        sys.argv[0] = str(script_path)
        runpy.run_path(str(script_path), run_name="__main__")
    except Exception as e:
        log.error(f"Error running {script_path}: {e}")
        raise SystemExit(1)

