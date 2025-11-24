#!/usr/bin/bash

#
# term-tree-screenshot-maker.sh [-e <env-file>] [-o <output-dir>]
#

#
# Functions
#
is_iterm2() {
	if [[ "${LC_TERMINAL-}" == "iTerm2" ]]; then
		return 0
	else
		return 1
	fi
}
it2_command() {
	# download function if iTerm extensions are installed; only used when running from ssh
	local command="$1"
	local file="$2"
    local IT2_DIR="$HOME/.iterm2"
    local IT2_COMMAND="$IT2_DIR/$command"

    if [[ -x "$IT2_COMMAND" ]]; then
        if [[ "${LC_TERMINAL-}" == "iTerm2" ]]; then
            "$IT2_COMMAND" "$file"
            return 0
        else
            printf '%s only available in iTerm2: cannot run %s on %s\n' "$IT2_COMMAND" "$command" "$file" >&2
            return 1
        fi
    else
        printf '%s not available in $HOME/.iterm2: cannot run %s on %s\n' "$IT2_COMMAND" "$command" "$file" >&2
        return 1
    fi
}

#
# Process command line arguments and setup global variables
#

# default values for command line arguments
ENV_FILE="USE_DUMMY_DATA"
OUTPUT_DIR="output"
# whether to delete temporary files after use
DEBUG_PRESERVE_TMP_FILES=1

# parse command line arguments
while getopts "e:o:" opt; do
    case $opt in
        e) ENV_FILE="$OPTARG" ;;
        o) OUTPUT_DIR="$OPTARG" ;;
        \?) echo "Invalid option: -$OPTARG" >&2
            echo "Usage: $0 [-e <env-file>] [-o <output-dir>]" >&2
            echo "  -h, --help: print this help message and exit" >&2
            echo "  -e <env-file>: path to the environment file to use for the data source.  If omitted, uses dummy data." >&2
            echo "  -o <output-dir>: directory to save the tree screenshot to.  If omitted, uses ./output." >&2
            exit 1 ;;
        -h|--help) echo "Usage: $0 [-e <env-file>] [-o <output-dir>]" >&2
            echo "  -h, --help: print this help message and exit" >&2
            echo "  -e <env-file>: path to the environment file to use for the data source.  If omitted, uses dummy data." >&2
            echo "  -o <output-dir>: directory to save the tree screenshot to.  If omitted, uses ./output." >&2
            exit 0 ;;
    esac
done

# width we will use for measuring number of lines and screenshotting
COLS=120
# initial height is arbitrary, will be adjusted once we measure line count
ROWS=10
# if the total number of rows exceeds this value, then we will chunk by this
# amount and generate multiple output files (tree-0.png, tree-1.png, etc.)
CHUNK_LINES_AMOUNT=50

# how many rows you want to add as buffer to the Konsole instances we screenshot
EXTRA_ROWS=1

PYTHON_SCRIPT="term-tree-maker"
if [[ "${ENV_FILE}" != "USE_DUMMY_DATA" ]]; then
    PYTHON_SCRIPT_ARGS="--env-file ${ENV_FILE}"
else
    PYTHON_SCRIPT_ARGS="--dummy-data"
fi
PNG_BASE_NAME="$(realpath -m "${OUTPUT_DIR}/tree")"
TREE_CROP_SCRIPT="term-tree-crop-util"

# debug output
echo "[term-tree-screenshot-maker] ENV_FILE:   ${ENV_FILE}" >&2
echo "[term-tree-screenshot-maker] OUTPUT_DIR: ${OUTPUT_DIR}" >&2

#
# Running from ssh => we need to re-invoke ourselves with `desktop-env-wrapper`
#
if [[ -n "${SSH_CONNECTION-}" || -n "${SSH_CLIENT-}" || -n "${SSH_TTY-}" ]]; then
	IN_SSH_SESSION=1
else
	IN_SSH_SESSION=0
fi
if [[ "$IN_SSH_SESSION" -eq 0 || "${IN_DESKTOP_ENV_WRAPPER-}" -eq 1 ]]; then
	echo "Running from local GUI desktop session, proceeding with script..."
else
	echo "Running from ssh, re-invoking with desktop-env-wrapper..."
	desktop-env-wrapper konsole --workdir "$PWD" -e bash -lc "term-tree-screenshot-maker -e ${ENV_FILE} -o ${OUTPUT_DIR}"
	exit_code=$?
	if [[ $exit_code -ne 0 ]]; then
		echo "❌ Failed to run term-tree-screenshot-maker" >&2
		exit $exit_code
	fi
	echo "✅ creation of '${PNG_BASE_NAME}.png' successful"
	if is_iterm2; then
		it2_command "it2dl" "${PNG_BASE_NAME}.png" && echo "✅ download of '${PNG_BASE_NAME}.png' successful" || echo "❌ download of '${PNG_BASE_NAME}.png' failed"
		it2_command "it2cat" "${PNG_BASE_NAME}.png" && echo "✅ display of '${PNG_BASE_NAME}.png' successful" || echo "❌ display of '${PNG_BASE_NAME}.png' failed"
	fi
	exit 0
fi

# --------------------------------------------------------------------------
# Main script
# --------------------------------------------------------------------------

# make the output dir if there is one
PNG_DIR=$(dirname "$PNG_BASE_NAME")
mkdir -p "$PNG_DIR"

# The first Konsole instance is just to count the number of lines we will print,
# sot that we can correctly size the second Konsole terminal.
TMP_FILE=/tmp/tree-width.tmp          # store number of lines here
TMP_FILE_CHUNKS=/tmp/tree-chunks.tmp  # store chunking variables here
TMP_WND_DIMENSIONS_JSON_FILE=/tmp/tree-window-dimensions.json # store window dimensions here
TMP_WND_DIMENSIONS_TMP_FILE_BASENAME=/tmp/tree-window-dimensions # store window dimensions here	

QT_QPA_PLATFORM=xcb \
PYTHON_SCRIPT="$PYTHON_SCRIPT" \
PYTHON_SCRIPT_ARGS="$PYTHON_SCRIPT_ARGS" \
TMP_FILE="$TMP_FILE" \
TMP_FILE_CHUNKS="$TMP_FILE_CHUNKS" \
CHUNK_LINES_AMOUNT="$CHUNK_LINES_AMOUNT" \
konsole \
	--profile TreeShot \
	-p "TerminalColumns=${COLS}" \
	-p "TerminalRows=${ROWS}" \
	--workdir "$PWD" \
	-e bash -lc '${PYTHON_SCRIPT} $PYTHON_SCRIPT_ARGS | wc -l > $TMP_FILE ; ${PYTHON_SCRIPT} $PYTHON_SCRIPT_ARGS -L $CHUNK_LINES_AMOUNT -q > $TMP_FILE_CHUNKS; '

ROWS_FROM_FILE=$(cat $TMP_FILE)
if [[ "$DEBUG_PRESERVE_TMP_FILES" -ne 1 ]]; then
	[ -f $TMP_FILE ] && rm -f $TMP_FILE
else
	echo "DEBUG_PRESERVE_TMP_FILES is set, preserving $TMP_FILE"
fi
eval "$(cat $TMP_FILE_CHUNKS)"
if [[ "$DEBUG_PRESERVE_TMP_FILES" -ne 1 ]]; then
	[ -f $TMP_FILE_CHUNKS ] && rm -f $TMP_FILE_CHUNKS
else
	echo "DEBUG_PRESERVE_TMP_FILES is set, preserving $TMP_FILE_CHUNKS"
fi

# --preserve-originals option if debugging is enabled
if [[ "$DEBUG_PRESERVE_TMP_FILES" -eq 1 ]]; then
	PRESERVE_ORIGINALS="--preserve-originals"
else
	PRESERVE_ORIGINALS=""
fi

if [[ "$CHUNK_LINES_AMOUNT" -gt "$ROWS_FROM_FILE" ]]; then
	ROWS=$(($EXTRA_ROWS+$ROWS_FROM_FILE))
    echo "Using ROWS=$ROWS, COLS=$COLS, no chunking"

	# init the window dimensions json file
	printf '[\n' > ${TMP_WND_DIMENSIONS_JSON_FILE}

	# Run the screenshot Konsole instance 
	PYTHON_SCRIPT="$PYTHON_SCRIPT" \
	PYTHON_SCRIPT_ARGS="$PYTHON_SCRIPT_ARGS" \
	TMP_WND_DIMENSIONS_TMP_FILE_BASENAME="$TMP_WND_DIMENSIONS_TMP_FILE_BASENAME" \
	QT_QPA_PLATFORM=xcb \
	konsole \
		--profile TreeShot \
		-p "TerminalColumns=${COLS}" \
		-p "TerminalRows=${ROWS}" \
		--workdir "$PWD" \
		--hide-menubar \
		--hide-tabbar \
		-e bash -lc 'clear ; sleep 1 ; $PYTHON_SCRIPT $PYTHON_SCRIPT_ARGS ; gnome-screenshot -d 1 -w -f ${PNG_BASE_NAME}.png ; xwininfo -root -tree | grep TREESHOT > ${TMP_WND_DIMENSIONS_TMP_FILE_BASENAME}.tmp'

	# grab width and height of the tree window
	awk 'match($0,/([0-9]+)x([0-9]+)\+([0-9]+)\+([0-9]+)/,m){
		printf "    {\n"
		printf "        \"windowWidth\": %s,\n",      m[1]
		printf "        \"windowHeight\": %s,\n",     m[2]
		printf "        \"windowPositionX\": %s,\n",  m[3]
		printf "        \"windowPositionY\": %s,\n",   m[4]
	}' ${TMP_WND_DIMENSIONS_TMP_FILE_BASENAME}.tmp >> ${TMP_WND_DIMENSIONS_JSON_FILE}
	printf "        \"rows\": %s,\n" "$ROWS" >> ${TMP_WND_DIMENSIONS_JSON_FILE}
	printf "        \"cols\": %s\n" "$COLS" >> ${TMP_WND_DIMENSIONS_JSON_FILE}
	printf "    }\n" >> ${TMP_WND_DIMENSIONS_JSON_FILE}

	# remove the temporary file
	if [[ "$DEBUG_PRESERVE_TMP_FILES" -ne 1 ]]; then
		[ -f ${TMP_WND_DIMENSIONS_TMP_FILE_BASENAME}.tmp ] && rm -f ${TMP_WND_DIMENSIONS_TMP_FILE_BASENAME}.tmp
	else
		echo "DEBUG_PRESERVE_TMP_FILES is set, preserving ${TMP_WND_DIMENSIONS_TMP_FILE_BASENAME}.tmp"
	fi
	# close the json array
	printf '\n]\n' >> ${TMP_WND_DIMENSIONS_JSON_FILE}

	# In-place crop the tree image
	${TREE_CROP_SCRIPT} ${PRESERVE_ORIGINALS} --window-dimensions-json-file ${TMP_WND_DIMENSIONS_JSON_FILE} ${PNG_BASE_NAME}.png && echo "✅ Cropped tree image saved to ${PNG_BASE_NAME}.png" || echo "❌ Failed to crop tree image"

	# remove the temporary json file
	if [[ "$DEBUG_PRESERVE_TMP_FILES" -ne 1 ]]; then
		[ -f ${TMP_WND_DIMENSIONS_JSON_FILE} ] && rm -f ${TMP_WND_DIMENSIONS_JSON_FILE}
	else
		echo "DEBUG_PRESERVE_TMP_FILES is set, preserving ${TMP_WND_DIMENSIONS_JSON_FILE}"
	fi

	# (debugging only) open the cropped tree image
	xdg-open ${PNG_BASE_NAME}.png
else
    echo "Using ROWS=$ROWS, COLS=$COLS, chunking: $(($CHUNKS_COUNT-1)) chunks of $CHUNK_LINES_AMOUNT lines, plus a final chunk with $LAST_CHUNK_LINE_COUNT lines"

	# init the window dimensions json file
	printf '[\n' > ${TMP_WND_DIMENSIONS_JSON_FILE}
	
    # Run the screenshot Konsole instance for each chunk
    for i in $(seq 0 $((CHUNKS_COUNT-1))); do
		if [[ "$i" -eq $((CHUNKS_COUNT-1)) ]]; then
			# last iteration
			ROWS=$(($EXTRA_ROWS+$LAST_CHUNK_LINE_COUNT))
			JSON_COMMA=""
		else
			# first (n-1) iterations -> we use the chunk size
			ROWS=$(($EXTRA_ROWS+$CHUNK_LINES_AMOUNT))
			JSON_COMMA=',\n'
		fi
        echo "Running screenshot Konsole instance for chunk $i"

		PYTHON_SCRIPT="$PYTHON_SCRIPT" \
		PYTHON_SCRIPT_ARGS="$PYTHON_SCRIPT_ARGS" \
		QT_QPA_PLATFORM=xcb \
		CHUNK_LINES_AMOUNT="$CHUNK_LINES_AMOUNT" \
		PNG_BASE_NAME="$PNG_BASE_NAME" \
		TMP_WND_DIMENSIONS_TMP_FILE_BASENAME="$TMP_WND_DIMENSIONS_TMP_FILE_BASENAME" \
		IDX="$i" \
		konsole \
            --profile TreeShot \
            -p "TerminalColumns=${COLS}" \
            -p "TerminalRows=${ROWS}" \
            --workdir "$PWD" \
			--hide-menubar \
			--hide-tabbar \
            -e bash -lc 'clear ; sleep 1 ; $PYTHON_SCRIPT $PYTHON_SCRIPT_ARGS -L $CHUNK_LINES_AMOUNT -l $IDX ; gnome-screenshot -d 1 -w -f $PNG_BASE_NAME-$IDX.png; xwininfo -root -tree | grep TREESHOT > ${TMP_WND_DIMENSIONS_TMP_FILE_BASENAME}-${IDX}.tmp'

		# grab width and height of the tree window
		awk 'match($0,/([0-9]+)x([0-9]+)\+([0-9]+)\+([0-9]+)/,m){
			printf "    {\n"
			printf "        \"windowWidth\": %s,\n",      m[1]
			printf "        \"windowHeight\": %s,\n",     m[2]
			printf "        \"windowPositionX\": %s,\n",  m[3]
			printf "        \"windowPositionY\": %s,\n",   m[4]
		}' ${TMP_WND_DIMENSIONS_TMP_FILE_BASENAME}-${i}.tmp >> ${TMP_WND_DIMENSIONS_JSON_FILE}
		printf "        \"rows\": %s,\n" "$ROWS" >> ${TMP_WND_DIMENSIONS_JSON_FILE}
		printf "        \"cols\": %s\n" "$COLS" >> ${TMP_WND_DIMENSIONS_JSON_FILE}
		printf "    }${JSON_COMMA}" >> ${TMP_WND_DIMENSIONS_JSON_FILE}

		# remove the temporary file
		if [[ "$DEBUG_PRESERVE_TMP_FILES" -ne 1 ]]; then
			[ -f ${TMP_WND_DIMENSIONS_TMP_FILE_BASENAME}-${i}.tmp ] && rm -f ${TMP_WND_DIMENSIONS_TMP_FILE_BASENAME}-${i}.tmp
		else
			echo "DEBUG_PRESERVE_TMP_FILES is set, preserving ${TMP_WND_DIMENSIONS_TMP_FILE_BASENAME}-${i}.tmp"
		fi
	done

	# close the json array
	printf '\n]\n' >> ${TMP_WND_DIMENSIONS_JSON_FILE}

	# In-place crop the tree images
	COMBINED_PNG="${PNG_BASE_NAME}.png"
	PNG_FILES=()
	for i in $(seq 0 $((CHUNKS_COUNT-1))); do
		PNG_FILES+=("${PNG_BASE_NAME}-${i}.png")
	done
	if ${TREE_CROP_SCRIPT} ${PRESERVE_ORIGINALS} --window-dimensions-json-file ${TMP_WND_DIMENSIONS_JSON_FILE} --output-path "${COMBINED_PNG}" "${PNG_FILES[@]}"; then
		echo "✅ Cropped tree image saved to ${COMBINED_PNG}"
	else
		echo "❌ Failed to crop tree images into ${COMBINED_PNG}"
	fi

	# remove the temporary json file
	if [[ "$DEBUG_PRESERVE_TMP_FILES" -ne 1 ]]; then
		[ -f ${TMP_WND_DIMENSIONS_JSON_FILE} ] && rm -f ${TMP_WND_DIMENSIONS_JSON_FILE}
	else
		echo "DEBUG_PRESERVE_TMP_FILES is set, preserving ${TMP_WND_DIMENSIONS_JSON_FILE}"
	fi

	# delete the images that have now been stacked and debug display the final combined image
	for i in $(seq 0 $((CHUNKS_COUNT-1))); do
		if [[ "$DEBUG_PRESERVE_TMP_FILES" -ne 1 ]]; then
			[[ -f "${PNG_BASE_NAME}-${i}.png" ]] && rm -f "${PNG_BASE_NAME}-${i}.png"
		else
			echo "DEBUG_PRESERVE_TMP_FILES is set, preserving ${PNG_BASE_NAME}-${i}.png"
		fi
	done
	xdg-open "${COMBINED_PNG}" && echo "✅ Opened ${COMBINED_PNG}" || echo "❌ Failed to open ${COMBINED_PNG}"
fi