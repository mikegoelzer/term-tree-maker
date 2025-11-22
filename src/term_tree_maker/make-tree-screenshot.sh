#!/usr/bin/bash

# width we will use for measuring number of lines and screenshotting
COLS=120
# initial height is arbitrary, will be adjusted once we measure line count
ROWS=10
# if the total number of rows exceeds this value, then we will chunk by this
# amount and generate multiple output files (tree-0.png, tree-1.png, etc.)
CHUNK_LINES_AMOUNT=50

# how many rows you want to add as buffer to the second Konsole instance
EXTRA_ROWS=2

PYTHON_SCRIPT="./tree.py"
PNG_BASE_NAME="${1:-output/tree}"

# make the output dir if there is one
PNG_DIR=$(dirname "$PNG_BASE_NAME")
if [[ "$PNG_DIR" != "." ]]; then
	mkdir -p "$PNG_DIR"
fi

# The first Konsole instance is just to count the number of lines we will print,
# sot that we can correctly size the second Konsole terminal.
TMP_FILE=/tmp/tree-width.tmp          # store number of lines here
TMP_FILE_CHUNKS=/tmp/tree-chunks.tmp  # store chunking variables here

PYTHON_SCRIPT="$PYTHON_SCRIPT" \
TMP_FILE="$TMP_FILE" \
TMP_FILE_CHUNKS="$TMP_FILE_CHUNKS" \
CHUNK_LINES_AMOUNT="$CHUNK_LINES_AMOUNT" \
konsole \
	--profile TreeShot \
	-p "TerminalColumns=${COLS}" \
	-p "TerminalRows=${ROWS}" \
	--workdir "$PWD" \
	-e bash -lc '${PYTHON_SCRIPT} | wc -l > $TMP_FILE ; ${PYTHON_SCRIPT} -L $CHUNK_LINES_AMOUNT -q > $TMP_FILE_CHUNKS; '

ROWS_FROM_FILE=$(cat $TMP_FILE)
# [ -f $TMP_FILE ] && rm -f $TMP_FILE
eval "$(cat $TMP_FILE_CHUNKS)"
# [ -f $TMP_FILE_CHUNKS ] && rm -f $TMP_FILE_CHUNKS

if [[ "$CHUNK_LINES_AMOUNT" -gt "$ROWS_FROM_FILE" ]]; then
	ROWS=$(($EXTRA_ROWS+$ROWS_FROM_FILE))
    echo "Using ROWS=$ROWS, COLS=$COLS, no chunking"

	# Run the screenshot Konsole instance 
	PYTHON_SCRIPT="$PYTHON_SCRIPT" \
	konsole \
		--profile TreeShot \
		-p "TerminalColumns=${COLS}" \
		-p "TerminalRows=${ROWS}" \
		--workdir "$PWD" \
		-e bash -lc 'clear ; sleep 1 ; $PYTHON_SCRIPT ; gnome-screenshot -w -f ${PNG_BASE_NAME}.png'

	# In-place crop the tree image
	./tree-crop.py ${PNG_BASE_NAME}.png && echo "✅ Cropped tree image saved to ${PNG_BASE_NAME}.png" || echo "❌ Failed to crop tree image"

	# (debugging only) open the cropped tree image
	xdg-open ${PNG_BASE_NAME}.png
else
    echo "Using ROWS=$ROWS, COLS=$COLS, chunking: $(($CHUNKS_COUNT-1)) chunks of $CHUNK_LINES_AMOUNT lines, plus a final chunk with $LAST_CHUNK_LINE_COUNT lines"

    # Run the screenshot Konsole instance for each chunk
    for i in $(seq 0 $((CHUNKS_COUNT-1))); do
		if [[ "$i" -eq $((CHUNKS_COUNT-1)) ]]; then
			# last iteration
			ROWS=$(($EXTRA_ROWS+$LAST_CHUNK_LINE_COUNT))
		else
			# first (n-1) iterations -> we use the chunk size
			ROWS=$(($EXTRA_ROWS+$CHUNK_LINES_AMOUNT))
		fi
        echo "Running screenshot Konsole instance for chunk $i"

		PYTHON_SCRIPT="$PYTHON_SCRIPT" \
		CHUNK_LINES_AMOUNT="$CHUNK_LINES_AMOUNT" \
		PNG_BASE_NAME="$PNG_BASE_NAME" \
		IDX="$i" \
		konsole \
            --profile TreeShot \
            -p "TerminalColumns=${COLS}" \
            -p "TerminalRows=${ROWS}" \
            --workdir "$PWD" \
            -e bash -lc 'clear ; sleep 1 ; $PYTHON_SCRIPT -L $CHUNK_LINES_AMOUNT -l $IDX ; gnome-screenshot -w -f $PNG_BASE_NAME-$IDX.png'
	done

	# In-place crop the tree images
	COMBINED_PNG="${PNG_BASE_NAME}.png"
	PNG_FILES=()
	for i in $(seq 0 $((CHUNKS_COUNT-1))); do
		PNG_FILES+=("${PNG_BASE_NAME}-${i}.png")
	done
	if ./tree-crop.py --output-path "${COMBINED_PNG}" "${PNG_FILES[@]}"; then
		echo "✅ Cropped tree image saved to ${COMBINED_PNG}"
	else
		echo "❌ Failed to crop tree images into ${COMBINED_PNG}"
	fi

	# delete the images that have now been stacked and debug display the final combined image
	for i in $(seq 0 $((CHUNKS_COUNT-1))); do
		#[[ -f "${PNG_BASE_NAME}-${i}.png" ]] && rm -f "${PNG_BASE_NAME}-${i}.png"
		xdg-open "${PNG_BASE_NAME}-${i}.png" && echo "✅ Opened ${PNG_BASE_NAME}-${i}.png" || echo "❌ Failed to open ${PNG_BASE_NAME}-${i}.png"
	done
	xdg-open "${COMBINED_PNG}" && echo "✅ Opened ${COMBINED_PNG}" || echo "❌ Failed to open ${COMBINED_PNG}"
fi