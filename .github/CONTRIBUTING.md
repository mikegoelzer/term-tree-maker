# Contributing to term-tree-maker

term-tree-maker is packaged with [`uv`](https://github.com/astral-sh/uv) + `hatch-vcs`. Everything from local development to PyPI releases flows through those tools. This document covers:

- Spinning up a dev environment and running the CLI/utility scripts.
- One-time desktop preparation (`install.sh`).
- How versioning works (git tags) and how to cut/publish a release.

---

## 1. Getting started

```bash
# 1) Clone and enter the repo
git clone git@github.com:curvcpu/tree-maker.git
cd tree-maker

# 2) Sync dependencies (creates .venv/) with dev extras such as pytest
uv sync --dev

# 3) Activate the virtualenv (optional because `uv run ...` works too)
source .venv/bin/activate

# 4) One-time desktop prep (must be executed from the physical GNOME console)
#    This installs desktop-env-wrapper and creates the Konsole profile used
#    by the screenshot tooling.
./install.sh
```

- Step 4 **must** be run in person (or via RDP) on the Ubuntu GNOME desktop. Running it over SSH will fail on purpose. After it completes once on the workstation, remote SSH sessions can drive the screenshot tooling through the wrappers documented below.
- To update dependencies later, re-run `uv sync --dev`.

### Common CLI commands

Once the package is installed (either locally via `uv sync` or from PyPI), the console entrypoints are available everywhere on your PATH:

| Command | Purpose |
|---------|---------|
| `tree` | Runs `tree.py` directly. All CLI flags from the original script still work. |
| `make-tree-screenshot` | Launches Konsole + gnome-screenshot to capture the tree output into PNG chunks. |
| `make-png-from-ssh` | Convenience wrapper that kicks off the screenshot workflow from an SSH session; downloads PNGs via iTerm’s `it2dl` helper when available. |

Examples:

```bash
# render the tree text locally
uv run tree --chunk-lines-amount 70 --chunk-count

# capture a screenshot locally after install.sh has configured the desktop tools
uv run make-tree-screenshot output/my-tree

# from SSH: run the remote workflow and download PNG(s) via iTerm helpers
make-png-from-ssh
```

### Running tests / lint

```bash
uv run pytest
```

(More tests will be added, but the dependency and command are ready.)

### Handy Make targets

Common workflows are wrapped in `Makefile`:

| Command | Description |
|---------|-------------|
| `make test` | Runs the pytest suite. |
| `make clean` | Removes build artifacts (`dist/`, `.pytest_cache/`, `.venv/`, etc.). |
| `make publish-patch` | Runs tests, bumps the patch version (`scripts/bump_version.py patch --push`), and creates the GitHub Release. |
| `make publish-minor` | Same flow, bumping the minor version (the helper script prompts before pushing). |
| `make publish-major` | Same flow for major bumps; push confirmation is mandatory. |

---

## 2. Versioning & release process

`term-tree-maker` uses `hatch-vcs` to derive its version number directly from git tags that match the pattern `term-tree-maker-v<MAJOR>.<MINOR>.<PATCH>`. No files need manual editing—bumping the version = creating the right tag.

### Choosing the new version (helper script)

Use `scripts/bump_version.py` to increment and tag the next semantic version automatically:

```bash
# make sure you're on an up-to-date main
git switch main
git pull origin main

# bump patch / minor / major (add --push to push the tag automatically)
uv run python scripts/bump_version.py patch --push
# uv run python scripts/bump_version.py minor --push
# uv run python scripts/bump_version.py major --push
```

The script looks at existing tags, calculates the next semantic version, creates the `term-tree-maker-vX.Y.Z` tag, and optionally pushes it to `origin`. When `--push` is supplied for **minor** or **major** bumps, you’ll be prompted to confirm before the tag is pushed; patch bumps push immediately without prompting.

### Publishing to PyPI via GitHub Actions

1. **Push the tag** so GitHub knows about it (skip if you already passed `--push` to the helper script):
   ```bash
   git push origin term-tree-maker-v${NEW_VERSION}
   ```
2. **Create a GitHub Release** from that tag (UI works great, or CLI):
   ```bash
   gh release create term-tree-maker-v${NEW_VERSION} \
     --title "term-tree-maker v${NEW_VERSION}" \
     --notes "Describe highlights here."
   ```
3. Publishing the release triggers `.github/workflows/release.yml`, which:
   - Checks out the repo.
   - Uses `uv build` to produce sdists/wheels from the tagged commit.
   - Uploads the artifacts to PyPI using trusted publishing (OIDC), so no secrets are needed.
4. Monitor the GitHub Actions run. When it finishes green, verify on PyPI:
   ```bash
   pip install --upgrade term-tree-maker
   ```

If something goes wrong, delete the GitHub Release (which also deletes the tag), fix the issue, re-tag, and repeat the steps above.

---

## 3. Summary checklist

1. Clone + `uv sync --dev`.
2. Run `./install.sh` from the GNOME desktop once per workstation.
3. Develop / test with `uv run tree`, `uv run pytest`, etc.
4. To release: tag (`term-tree-maker-vX.Y.Z`), push, create GitHub Release, monitor CI, and confirm on PyPI.

Thanks for helping improve term-tree-maker!


