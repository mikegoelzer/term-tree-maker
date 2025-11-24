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

After installing, one console command is available everywhere on your PATH:

| Command | Description |
|---------|-------------|
| `term-tree-maker` | Runs the packaged `term_tree_maker.py` script that generates the text-based tree visualization. All original CLI flags still work. |

Example:

```bash
term-tree-maker --chunk-lines-amount 70 --chunk-count --dummy-data
```

## Installation

- Run the installation script one time from a Gnome or KDE console.  You must be physically at the machine or connected over VNC/RDP.  This will **NOT work over SSH**:

```bash
cd <this directory>
# requires sudo privileges:
./install.sh && echo "✅ Installed term-tree-maker" >&1 || echo "❌ Failed to install term-tree-maker" >&2
```

<!-- 
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
-->

## Usage

- From an SSH session into the server where the term-tree-maker is installed:

```bash
[user@server] term-tree-maker --chunk-lines-amount 70 --chunk-count --dummy-data
```