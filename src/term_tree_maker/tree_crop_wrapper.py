import runpy
import sys
from pathlib import Path
import logging
import subprocess
import logging

log = logging.getLogger(__name__)

def main() -> None:
    """
    Console entrypoint for the ``tree-crop`` command.

    This simply executes the original ``tree_crop.py`` script inside the
    installed package, forwarding any command-line arguments.
    """
    try:
        package_dir = Path(__file__).resolve().parent
        script_path = package_dir / "tree_crop.py"

        result = subprocess.run(
            [str(script_path), *sys.argv[1:]],
            stdout=sys.stdout,
            stderr=sys.stderr,
            text=True,
            cwd=str(package_dir),
            check=True,
        )
    except Exception as e:
        log.error(f"Error running {script_path}: {e}")
        raise SystemExit(1)
    log.info(f"[tree-crop-wrapper] stdout: {result.stdout}")
    log.info(f"[tree-crop-wrapper] stderr: {result.stderr}")
    raise SystemExit(result.returncode)

