import subprocess
import sys
from pathlib import Path


def main() -> None:
    """
    Console entrypoint for ``make-tree-screenshot``.

    This wraps the original ``make-tree-screenshot.sh`` shell script that
    lives inside the installed ``term_tree_maker`` package, forwarding
    all arguments.
    """
    package_dir = Path(__file__).resolve().parent
    script_path = package_dir / "make-tree-screenshot.sh"

    cmd = ["bash", str(script_path), *sys.argv[1:]]
    raise SystemExit(
        subprocess.call(
            cmd,
            cwd=str(package_dir),
        )
    )


