import subprocess
import sys
from pathlib import Path


def main() -> None:
    """
    Console entrypoint for ``make-png-from-ssh``.

    This wraps the original ``make-png-from-ssh.sh`` shell script that
    lives inside the installed ``term_tree_maker`` package, forwarding
    all arguments.
    """
    package_dir = Path(__file__).resolve().parent
    script_path = package_dir / "make-png-from-ssh.sh"

    cmd = ["bash", str(script_path), *sys.argv[1:]]
    raise SystemExit(
        subprocess.call(
            cmd,
            cwd=str(package_dir),
        )
    )


