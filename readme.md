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
| `term-tree-maker` | Runs the packaged `term_tree_maker.py` script that generates the text-based tree visualization. All original CLI flags still work. |
| `term-tree-screenshot-maker` | Launches the Konsole/gnome-screenshot workflow to capture the tree output into PNGs (wraps `term-tree-screenshot-maker.sh`). |
| `term-tree-crop-util` | Utility for cropping the tree screenshot into a single PNG file. This is an internal utility used by `term-tree-screenshot-maker` and doesn't need to be run manually.|

Each command accepts the same arguments as its original script. Example:

```bash
term-tree-maker --chunk-lines-amount 70 --chunk-count --dummy-data
term-tree-screenshot-maker -o output -e .env
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
[user@server] term-tree-screenshot-maker -o output -e .env
[user@server] it2dl output/tree.png   # download the tree image to your local machine
[user@server] imgcat output/tree.png  # display the tree image in your local terminal
```

- Or run the screenshot workflow locally (GNOME desktop session) with a custom output prefix:

```bash
term-tree-screenshot-maker -o output -e .env
```