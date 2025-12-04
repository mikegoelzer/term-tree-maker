# `tree-maker`

A tool to display a text-based tree of nodes defined in Python code and make a screenshot of the tree.

## Installation

`term-tree-maker` is published on PyPI. 

Install it with whichever tool you prefer:

```bash
# Option 1: using `uv`
uv pip install term-tree-maker

# Option 2: using plain `pip`
python -m pip install --upgrade pip
python -m pip install term-tree-maker

# Option 3: using `pipx`
pipx install term-tree-maker
```

Run the installation script one time from a Gnome or KDE console.  You must be physically at the machine or connected over VNC/RDP.  This will **NOT work over SSH**:

```bash
cd <this directory>
# requires sudo privileges:
./install.sh && echo "✅ Installed term-tree-maker" >&1 || echo "❌ Failed to install term-tree-maker" >&2
```

`install.sh` creates a Konsole profile in your home directory, and also installs a wrapper script in `/usr/local/bin` that launches Konsole with the correct GUI console environment from SSH sessions.

## CLI overview

After installing, two console commands are available everywhere on your PATH:

| Command                 | Description |
|-------------------------|-------------|
| `tree-maker`            | Runs the packaged `term_tree_maker.py` script that generates the text-based tree visualization. All original CLI flags still work. |
| `tree-screenshot-maker` | Launches Konsole + gnome-screenshot to capture the tree output into PNG chunks. |


Usage examples are provided below.

## Usage

From either a local GUI desktop session or an SSH session into the server where the `tree-maker` and `tree-screenshot-maker` are installed, you can run the following commands:

```bash
[user@server] tree-maker --chunk-lines-amount 70 --chunk-count --dummy-data
```

```bash
[user@server] tree-screenshot-maker -o output -e .env
```
