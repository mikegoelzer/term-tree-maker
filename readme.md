# tree-maker

A tool to make a screenshot of a tree of nodes defined in Python code.

## Install via pip/uv

term-tree-maker is published on PyPI. Install it with whichever tool you prefer:

```bash
# using uv
uv pip install term-tree-maker

# or plain pip
python -m pip install --upgrade pip
python -m pip install term-tree-maker
```

## CLI overview

After installing, three console commands are available everywhere on your PATH:

| Command | Description |
|---------|-------------|
| `tree` | Runs the packaged `tree.py` script that generates the text-based tree visualization. All original CLI flags still work. |
| `make-tree-screenshot` | Launches the Konsole/gnome-screenshot workflow to capture the tree output into PNGs (wraps `make-tree-screenshot.sh`). |
| `make-png-from-ssh` | Convenience wrapper for invoking the screenshot workflow from an SSH session (wraps `make-png-from-ssh.sh`). |

Each command accepts the same arguments as its original script. Example:

```bash
tree --chunk-lines-amount 70 --chunk-count
make-tree-screenshot output/my-tree
make-png-from-ssh
```

> **Note:** The first-time desktop environment preparation (`install.sh`) is still required on the target GNOME machine. See [`CONTRIBUTING.md`](.github/CONTRIBUTING.md) for the full setup checklist.

## Installation

- From the Gnome console (physically at the machine or over RDP):

```bash
cd <this directory>
[ -f $PWD/src/term_tree_maker/make-tree-screenshot.sh ] && echo "✅ good you're in the right dir: $PWD" || echo "ERROR: you're in the wrong dir"
```

The above just verifies that we are in the right directory because `install.sh` won't work otherwise.  It writes config files the current value of `$PWD`.


```bash
./install.sh && echo "✅ Installed tree-maker" >&1 || ( echo "❌ Failed to install tree-maker" >&2 && exit 1 )
```

- Append this to your `~/.bashrc` to make it easier to run:

```bash
#
# allow gnome wayland desktop apps to be started from ssh sessiosn
#
export QT_QPA_PLATFORM=wayland
```

```bash
source ~/.bashrc
```

## Usage

- From an SSH session into the server where the tree-maker is installed:

```bash
[user@server] make-png-from-ssh
[user@server] it2dl tree.png   # download the tree image to your local machine
[user@server] imgcat tree.png  # display the tree image in your local terminal
```

- Or run the screenshot workflow locally (GNOME desktop session) with a custom output prefix:

```bash
make-tree-screenshot output/my-tree
```