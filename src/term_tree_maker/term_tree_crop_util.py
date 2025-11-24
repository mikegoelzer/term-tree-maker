#!/usr/bin/env -S uv run --script --extra dev --frozen

from PIL import Image
import os
import sys
from typing import Optional, List
import argparse
import logging
import shutil
from pathlib import Path
import json
import logging
from term_tree_maker import init_logging

log = logging.getLogger(__name__)

# TODO: this should automatically match with what's in tree-screenshot-maker.sh
EXTRA_ROWS = 1

def compute_char_width_and_height(window_dimensions: dict[str, int]) -> tuple[int, int]:
    w = window_dimensions['windowWidth'] // window_dimensions['cols']
    h = window_dimensions['windowHeight'] // window_dimensions['rows']
    return w, h

def crop_tree_image(img_path: str, output_path: Optional[str] = None, window_dimensions: Optional[dict[str, int]] = None) -> str:
    WIDTH_OF_CHAR, HEIGHT_OF_CHAR = compute_char_width_and_height(window_dimensions)
    
    excess_window_height = window_dimensions['windowHeight'] - (window_dimensions['rows']*HEIGHT_OF_CHAR)
    assert excess_window_height >= 0, f"excess_window_height is not >= 0: {excess_window_height}"
    bottom_excess_pixels = excess_window_height // 2
    top_excess_pixels = excess_window_height - bottom_excess_pixels
    log.info(f"excess_window_height: {excess_window_height}, top_excess_pixels: {top_excess_pixels}, bottom_excess_pixels: {bottom_excess_pixels}")

    scroll_bar_width = window_dimensions['windowWidth'] - (window_dimensions['cols']*WIDTH_OF_CHAR)
    assert scroll_bar_width >= 0, f"scroll_bar_width is not >= 0: {scroll_bar_width}"
    log.info(f"scroll_bar_width: {scroll_bar_width}")

    top_trim    = top_excess_pixels
    right_trim  = scroll_bar_width
    bottom_trim = (EXTRA_ROWS*HEIGHT_OF_CHAR) + bottom_excess_pixels
    left_trim   = 0

    img = Image.open(img_path)
    w, h = img.size

    # (left, upper, right, lower)
    box = (left_trim, top_trim, w - right_trim, h - bottom_trim)
    cropped = img.crop(box)

    if output_path is None:
        output_path = img_path.replace(".png", "-cropped.png")
        cropped.save(output_path)
        os.rename(output_path, img_path)
        return img_path
    else:
        cropped.save(output_path)
        return output_path


def stack_images_vertically(image_paths: List[str]) -> Image.Image:
    if not image_paths:
        raise ValueError("No images to stack")

    images = [Image.open(p) for p in image_paths]
    widths = [im.width for im in images]
    if len(set(widths)) != 1:
        raise ValueError(f"Images must all have the same width, got widths={widths}")

    width = widths[0]
    total_height = sum(im.height for im in images)

    # Use mode of first image; convert others as needed
    mode = images[0].mode
    stacked = Image.new(mode, (width, total_height))

    y_offset = 0
    for im in images:
        if im.mode != mode:
            im = im.convert(mode)
        stacked.paste(im, (0, y_offset))
        y_offset += im.height

    return stacked


def parse_args():
    parser = argparse.ArgumentParser(
        description="Crop tree image(s) and optionally stack them vertically"
    )
    parser.add_argument(
        "--preserve-originals",
        '-p',
        action="store_true",
        default=False,
        help="Preserve original images after before cropping in place (saved as <IMG_PATH>.before-crop.png)",
    )
    parser.add_argument(
        "--window-dimensions-json-file",
        metavar="WINDOW_DIMENSIONS_JSON",
        type=str,
        default=None,
        help="JSON file containing window dimensions",
        required=True,
    )
    parser.add_argument(
        "img_paths",
        metavar="IMG_PATH",
        nargs="+",
        help="path(s) to image(s) to crop (order matters for stacking)",
    )
    parser.add_argument(
        "--output-path",
        metavar="OUTPUT",
        default=None,
        help=(
            "where to write output; for multiple inputs this is the combined PNG; "
            "for a single input this is the cropped image. "
            "If omitted: single input → in-place, multiple inputs → ./combined.png"
        ),
    )
    args = parser.parse_args()
    args.window_dimensions_json_file = Path(args.window_dimensions_json_file)
    if not args.window_dimensions_json_file.exists() or not args.window_dimensions_json_file.is_file():
        raise FileNotFoundError(f"Window dimensions JSON file not found: {args.window_dimensions_json_file}")
    return args


def main():
    args = parse_args()

    with open(args.window_dimensions_json_file, "r", encoding="utf-8") as f:
        window_dimensions = json.load(f)
    log.info(f"Window dimensions from file {args.window_dimensions_json_file}: ")
    log.info(json.dumps(window_dimensions, indent=4))

    if len(args.img_paths) == 1:
        # Single-image mode
        img_path = args.img_paths[0]
        cropped = crop_tree_image(img_path, args.output_path, window_dimensions=window_dimensions[0])
        log.info(f"Cropped image saved to: {cropped}")
    else:
        # Multi-image mode: crop all and stack vertically
        cropped_image_paths = []
        for i,p in enumerate(args.img_paths):
            if args.preserve_originals:
                shutil.copyfile(p, p.replace(".png", ".before-crop.png"))
                log.info(f"Preserved original image: {p.replace('.png', '.before-crop.png')}")
            log.info(f"Cropping image: {p} ({i+1} of {len(args.img_paths)})")
            cropped_image_paths.append(crop_tree_image(p, window_dimensions=window_dimensions[i]))
        stacked = stack_images_vertically(cropped_image_paths)

        if args.output_path is None:
            output_path = "combined.png"
        else:
            output_path = args.output_path

        stacked.save(output_path)
        log.info(f"Combined cropped image saved to: {output_path}")


if __name__ == "__main__":
    try:
        init_logging()
        sys.exit(main())
    except SystemExit as e:
        sys.exit(e.code)
    except Exception as e:
        log.exception(f"Error: {e}")
        raise SystemExit(1)
