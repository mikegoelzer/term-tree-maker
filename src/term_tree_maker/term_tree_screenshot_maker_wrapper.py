import subprocess
import sys
import os
from pathlib import Path
import logging
from term_tree_maker import init_logging
from term_tree_maker.settings import get_env_or_defaults

log = logging.getLogger(__name__)

def main() -> None:
    """
    Console entrypoint for ``term-tree-screenshot-maker``.

    This wraps the original ``term-tree-screenshot-maker.sh`` shell script inside
    the installed ``term_tree_maker`` package, forwarding all arguments.
    """
    env_value:dict[str, int | str] = {}
    try:
        init_logging()
        env_values = get_env_or_defaults()
    except Exception as e:
        log.critical(f"ERROR: could not initialize logging: %s", e, exc_info=True)
        raise SystemExit(1) from e

    # make sure env_values are in the environment
    for k,v in env_values.items():
        assert str(os.environ.get(k)) == str(v)

    package_dir = Path(__file__).resolve().parent
    script_path = package_dir / "term-tree-screenshot-maker.sh"
    wrapper_script_filename = Path(__file__).name

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
        log.error(f"ERROR: could not run {script_path}: {e}")
        raise SystemExit(1) from e

    log.info(f"[{wrapper_script_filename}] stdout: {result.stdout}")
    log.info(f"[{wrapper_script_filename}] stderr: {result.stderr}")
    sys.exit(result.returncode)

