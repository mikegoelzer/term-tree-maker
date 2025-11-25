# Contributing to `term-tree-maker`

`term-tree-maker` is packaged with [`uv`](https://github.com/astral-sh/uv) + `hatch-vcs`. Everything from local development to PyPI releases flows through those tools. This document covers:

- Spinning up a dev environment and running the CLI/utility scripts.
- One-time desktop preparation (`install.sh`).
- How versioning works (git tags) and how to cut/publish a release.

---

## 1. Getting started

```bash
# 1) Clone and enter the repo
git clone git@github.com:mikegoelzer/term-tree-maker.git
cd term-tree-maker

# 2) Sync dependencies (creates .venv/) with dev extras such as pytest
make install-dev

# 3) One-time desktop prep (must be executed from the physical GNOME console)
#  - This installs `desktop-env-wrapper` and creates the Konsole profile used
#    by the screenshot tooling.
#  - Require sudo privileges.
./install.sh
```

- Step 3 (`install.sh`) **must** be run in person (or via RDP/VNC) on the Ubuntu GNOME Wayland desktop. Running it over SSH will fail because the variables we need to store are not available. After it completes once on the workstation, remote SSH sessions can drive the screenshot tooling through the wrappers documented below.

- Be careful about re-running `uv sync`. It will blow away the local package install paths for `curvpyutils` and `curvtools` (see below), so you'll have to follow it with a new `make update-venv-for-dev`.

### Note on using editable local installs

The above instructions assume you have editable local installs of `curvpyutils` and `curvtools`. If you don't, you can use `make install-min` to install the package in non-editable mode.

If you do have editable local installs, you need to edit the Makefile to fix the relative paths to these local packages (look near the top for two lines that start with `LOCAL_CURVPYUTILS_PATH` and `LOCAL_CURVTOOLS_PATH`).

### Common CLI commands

Once the package is installed (either locally or from PyPI), the console entrypoints are available everywhere on your PATH:

| Command | Purpose |
|---------|---------|
| `term-tree-maker` | Runs `term_tree_maker.py` directly. All CLI flags from the original script still work. |
| `term-tree-screenshot-maker` | Launches Konsole + gnome-screenshot to capture the tree output into PNG chunks. |
| `term-tree-crop-util` | Utility that crops the tree output into PNG chunks. Usually not run directly, but used by `term-tree-screenshot-maker`.|

Examples:

```bash
# render the tree text locally
uv run tree --chunk-lines-amount 70 --chunk-count

# capture a screenshot locally on GUI desktopafter install.sh has configured the desktop tools
uv run make-tree-screenshot -o output -e .env

# from SSH: run the remote workflow and download PNG(s) via iTerm helpers
term-tree-screenshot-maker -o output -e .env
```

### Running tests / lint

```bash
make test
```

---

## 2. Versioning & release process

`term-tree-maker` uses `hatch-vcs` to derive its version number directly from git tags that match the pattern `term-tree-maker-v<MAJOR>.<MINOR>.<PATCH>`. No files need manual editing—bumping the version = creating the right tag.

### Choosing the new version (helper script)

Use `scripts/bump_version.py` to increment and tag the next semantic version automatically:

```bash
# make sure you're on an up-to-date main
git switch main
git pull origin main

# bump patch / minor / major
make bump-patch
# or:  make bump-minor
# or: make bump-major
```

The script looks at existing tags, calculates the next semantic version, creates the `term-tree-maker-vX.Y.Z` tag, and optionally pushes it to `origin`. When `--push` is supplied for **minor** or **major** bumps, you’ll be prompted to confirm before the tag is pushed; patch bumps push immediately without prompting.

### Publishing to PyPI via GitHub Actions

Here's the easy way:

```bash
make publish-patch
# or: make publish-minor
# or: make publish-major
```

Sit back and wait.

Here's the manual way:

1. **Push the tag** so GitHub knows about it (skip if you already passed `--push` to the helper script):
   ```bash
   git push origin term-tree-maker-v${NEW_VERSION}
   ```
2. **Create a GitHub Release** from that tag (UI works great, or CLI):
   ```bash
   gh release create term-tree-maker-v${NEW_VERSION} \
     --title "term-tree-maker-v${NEW_VERSION}" \
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

1. Clone + `make install-dev`.
2. Run `./install.sh` from the GNOME desktop once per workstation (required for the screenshot tooling only, not the basic tree maker).
3. Develop / test with `term-tree-maker`, `make test`, etc.
4. To release: `make publish-patch`, `make publish-minor`, `make publish-major`.

Thanks for helping improve `term-tree-maker`!
