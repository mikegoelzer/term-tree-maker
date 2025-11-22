import runpy
import sys
from pathlib import Path


def main() -> None:
    """
    Console entrypoint for the ``tree`` command.

    This simply executes the original ``tree.py`` script inside the
    installed package, forwarding any command-line arguments.
    """
    package_dir = Path(__file__).resolve().parent
    script_path = package_dir / "tree.py"

    # Emulate ``python tree.py ...`` semantics
    sys.argv[0] = str(script_path)
    runpy.run_path(str(script_path), run_name="__main__")


