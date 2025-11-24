import subprocess
import sys
import os
from pathlib import Path
import logging

log = logging.getLogger(__name__)

def main() -> None:
    """
    Console entrypoint for ``term-tree-screenshot-maker``.

    This wraps the original ``term-tree-screenshot-maker.sh`` shell script inside
    the installed ``term_tree_maker`` package, forwarding all arguments.
    """
    package_dir = Path(__file__).resolve().parent
    script_path = package_dir / "term-tree-screenshot-maker.sh"

    try:
        cmd = ["bash", str(script_path), *sys.argv[1:]]
        result = subprocess.run(
            cmd, 
            cwd=os.getcwd(),
            stdout=sys.stdout,
            stderr=sys.stderr,
            text=True,
            check=True,
        )
    except Exception as e:
        log.error(f"Error running {script_path}: {e}")
        raise SystemExit(1)
    log.info(f"[term_tree_screenshot_maker_wrapper] stdout: {result.stdout}")
    log.info(f"[term_tree_screenshot_maker_wrapper] stderr: {result.stderr}")
    raise SystemExit(result.returncode)

