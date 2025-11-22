#!/usr/bin/bash

if [[ -z "${SSH_CONNECTION-}" && -z "${SSH_CLIENT-}" && -z "${SSH_TTY-}" ]]; then
  echo "ERROR: make-tree-screenshot.sh must be run from ssh session, not from the linux GUI console itself" >&2
  exit 1
fi

TREE_SHOT_DIR=$(dirname $(realpath $PWD/make-tree-screenshot.sh))
[ -f $TREE_SHOT_DIR/make-tree-screenshot.sh ] || ( echo "ERROR: $TREE_SHOT_DIR/make-tree-screenshot.sh not found" >&2 && sleep 10 && exit 1 )

# make the output dir if there is one
PNG_BASE_NAME="output/tree"
PNG_DIR=$(dirname "$PNG_BASE_NAME")
if [[ "$PNG_DIR" != "." ]]; then
	mkdir -p "$PNG_DIR"
fi

# download function if iTerm extensions are installed
it2_download() {
    local file="$1"
    local IT2_DIR="$HOME/.iterm2"
    local IT2DL="$IT2_DIR/it2dl"

    if [[ -x "$IT2DL" ]]; then
        if [[ "${LC_TERMINAL-}" == "iTerm2" ]]; then
            "$IT2DL" "$file"
            return 0
        else
            printf 'it2dl only available in iTerm2: cannot download %s\n' "$file" >&2
            return 1
        fi
    else
        printf 'it2dl not available in $HOME/.iterm2: cannot download %s\n' "$file" >&2
        return 1
    fi
}
# delete old file before we start
[[ -d "$PNG_DIR" ]] && find "$PNG_DIR" -type f -name "*.png" -delete

# echo "TREE_SHOT_DIR: $TREE_SHOT_DIR"
# echo "Running: desktop-env-wrapper konsole --profile TreeShot --workdir "$TREE_SHOT_DIR" -e bash -lc 'cd "$TREE_SHOT_DIR" ; ./make-tree-screenshot.sh'"
desktop-env-wrapper konsole --profile TreeShot --workdir "$TREE_SHOT_DIR" -e bash -lc 'cd "$TREE_SHOT_DIR" ; ./make-tree-screenshot.sh "$PNG_BASE_NAME"'

# download the tree image to your local machine
PNG_BASE_FILE_NAME="$(basename $PNG_BASE_NAME)"
PNG_FILES_COUNT=$(find "${TREE_SHOT_DIR}/${PNG_DIR}" -type f -name "${PNG_BASE_FILE_NAME}-*.png" | wc -l)
for i in $(seq 0 $((PNG_FILES_COUNT-1))); do
    it2_download "${TREE_SHOT_DIR}/${PNG_BASE_NAME}-${i}.png" && echo "✅ Opened ${TREE_SHOT_DIR}/${PNG_BASE_NAME}-${i}.png" || echo "❌ Failed to open ${TREE_SHOT_DIR}/${PNG_BASE_NAME}-${i}.png"
done
it2_download "${TREE_SHOT_DIR}/${PNG_BASE_NAME}.png" && echo "✅ download of '${TREE_SHOT_DIR}/${PNG_BASE_NAME}.png' successful" || echo "❌ download of '${TREE_SHOT_DIR}/${PNG_BASE_NAME}.png' unsuccessful"
