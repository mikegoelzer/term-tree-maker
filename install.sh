#!/bin/bash

# Fail fast
set -euo pipefail

# ---- sanity checks ---------------------------------------------------------

# Must NOT be run over SSH
if [[ -n "${SSH_CONNECTION-}" || -n "${SSH_CLIENT-}" || -n "${SSH_TTY-}" ]]; then
  echo "ERROR: install.sh must be run from a local desktop session, not over SSH" >&2
  exit 1
fi

# Must have a GUI session (DISPLAY set)
if [[ -z "${DISPLAY-}" ]]; then
  echo "ERROR: DISPLAY is not set; are you in a GUI session?" >&2
  exit 1
fi

# ---- import the current GUI env into the user systemd instance -------------

systemctl --user import-environment \
  DISPLAY WAYLAND_DISPLAY XDG_RUNTIME_DIR DBUS_SESSION_BUS_ADDRESS XAUTHORITY

# ---- install /usr/local/bin/desktop-env-wrapper ----------------------------

sudo tee /usr/local/bin/desktop-env-wrapper >/dev/null <<'EOF'
#!/bin/bash

#
# Note: this script wraps any command, providing a GUI desktop environment based
# on pre-memorized systemd user environment variables.
#
# This script is useful for running commands over SSH to get a GUI desktop 
# environment. Any env vars already in caller's environment are propagated 
# to the wrapped command unchanged.
#
# Script also add a flag: IN_DESKTOP_ENV_WRAPPER=1 to the wrapped command's
# environment. This allows a script to detect if it has already been wrapped
# and is therefore already running in a GUI desktop environment.
#

# vars we care about
NEEDED_VARS=(
  DISPLAY
  WAYLAND_DISPLAY
  XDG_RUNTIME_DIR
  DBUS_SESSION_BUS_ADDRESS
  XAUTHORITY
)

# Read systemd user env and selectively export a few vars.
while IFS='=' read -r name value; do
  for v in "${NEEDED_VARS[@]}"; do
    if [[ "$name" == "$v" ]]; then
      # Use printf %q to handle weird chars if you want to be extra careful
      export "$name=$value"
      break
    fi
  done
done < <(systemctl --user show-environment)

export IN_DESKTOP_ENV_WRAPPER=1
exec "$@"
EOF

sudo chmod +x /usr/local/bin/desktop-env-wrapper

# Install the profile for Konsole to use with the tree-screenshot command
cat > ~/.local/share/konsole/TreeShot.profile <<EOF
[General]
Command=/bin/bash
Name=TreeShot
Parent=FALLBACK/
StartInCurrentSessionDir=false
TerminalColumns=80
TerminalRows=50
LocalTabTitleFormat=TREESHOT : %d : %n
RemoteTabTitleFormat=TREESHOT : (%u) %H

[Keyboard]
KeyBindings=macos

[Scrolling]
HistoryMode=2
EOF

echo "desktop-env-wrapper installed in /usr/local/bin"
