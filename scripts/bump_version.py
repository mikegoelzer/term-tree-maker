#!/usr/bin/env python3

from __future__ import annotations

EPILOG_TEXT="""
Usage:
    uv run python scripts/bump_version.py patch [-y]
    uv run python scripts/bump_version.py minor --push [-y]
    uv run python scripts/bump_version.py major [-y]

Options:
    -y, --no-prompt  Do not prompt for confirmation, just assume yes.
    --show-latest    Print the latest known version (no tagging) and exit.
    --push           Push the newly created tag to origin. Major/minor bumps 
                     will prompt for confirmation unless '-y' is specified.
"""

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Iterable

TAG_PREFIX = "term-tree-maker-v"
TAG_PATTERN = re.compile(rf"{TAG_PREFIX}(\d+)\.(\d+)\.(\d+)$")


@dataclass(order=True, frozen=True)
class Version:
    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def bump(self, part: str) -> "Version":
        if part == "major":
            return Version(self.major + 1, 0, 0)
        if part == "minor":
            return Version(self.major, self.minor + 1, 0)
        if part == "patch":
            return Version(self.major, self.minor, self.patch + 1)
        raise ValueError(f"Unknown part: {part}")


def run_git(args: Iterable[str]) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def get_latest_version() -> Version:
    tags = run_git(["tag", "--list", f"{TAG_PREFIX}*"])
    if not tags:
        return Version(0, 0, 0)

    versions: list[Version] = []
    for tag in tags.splitlines():
        match = TAG_PATTERN.fullmatch(tag.strip())
        if not match:
            continue
        versions.append(
            Version(
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3)),
            )
        )
    if not versions:
        return Version(0, 0, 0)
    return max(versions)


def tag_version(version: Version) -> None:
    tag_name = f"{TAG_PREFIX}{version}"
    subprocess.run(["git", "tag", tag_name], check=True)


def push_tag(version: Version) -> None:
    tag_name = f"{TAG_PREFIX}{version}"
    subprocess.run(["git", "push", "origin", tag_name], check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bump the semantic version and create a git tag.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=EPILOG_TEXT
    )
    parser.add_argument(
        "part",
        choices=("major", "minor", "patch"),
        nargs="?",
        help="Which part of the semantic version to increment.",
    )
    parser.add_argument(
        "--show-latest",
        action="store_true",
        help="Print the latest known version (no tagging) and exit.",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push the newly created tag to origin. Major/minor bumps will prompt for confirmation unless '-y' is specified.",
    )
    parser.add_argument(
        '-y', "--no-prompt", 
        dest="no_prompt",
        action="store_true", 
        default=False, 
        help="Do not prompt for confirmation, just assume yes. (Default: %(default)s).")
    return parser.parse_args()


def confirm(message: str) -> bool:
    try:
        from rich.prompt import Confirm
        return Confirm.ask(message, default=False)
    except Exception:
        resp = input(f"{message} [y/N]: ").strip().lower()
        return resp in {"y", "yes"}


def main() -> None:
    args = parse_args()
    if args.show_latest:
        print(get_latest_version())
        return
    if not args.part:
        print("error: you must specify which version part to bump", file=sys.stderr)
        sys.exit(2)
    current = get_latest_version()
    new_version = current.bump(args.part)
    tag_version(new_version)

    should_push = args.push
    if should_push and args.part in {"major", "minor"}:
        should_push = (args.no_prompt) or (confirm(f"Push tag {TAG_PREFIX}{new_version} to origin now?"))

    if should_push:
        push_tag(new_version)
        print(f"Tagged version {new_version} ({TAG_PREFIX}{new_version}) and pushed to origin.")
    else:
        print(f"Tagged version {new_version} ({TAG_PREFIX}{new_version})")
        print("Run `git push origin --tags` to publish the newly created tag.")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        print(f"Command failed: {exc}", file=sys.stderr)
        sys.exit(exc.returncode)

