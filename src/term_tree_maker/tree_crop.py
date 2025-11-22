#!/usr/bin/env -S uv run --script

from PIL import Image
import os
from typing import Optional, List
import argparse


def crop_tree_image(img_path: str, output_path: Optional[str] = None) -> str:
    top_trim    = 82
    right_trim  = 25
    bottom_trim = 34
    left_trim   = 5

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
    return parser.parse_args()


def main():
    args = parse_args()

    if len(args.img_paths) == 1:
        # Single-image mode
        img_path = args.img_paths[0]
        cropped = crop_tree_image(img_path, args.output_path)
        print(f"Cropped image saved to: {cropped}")
    else:
        # Multi-image mode: crop all and stack vertically
        cropped_image_paths = []
        for i,p in enumerate(args.img_paths):
            print(f"Cropping image: {p} ({i+1} of {len(args.img_paths)})")
            cropped_image_paths.append(crop_tree_image(p))
        stacked = stack_images_vertically(cropped_image_paths)

        if args.output_path is None:
            output_path = "combined.png"
        else:
            output_path = args.output_path

        stacked.save(output_path)
        print(f"Combined cropped image saved to: {output_path}")


if __name__ == "__main__":
    main()




# from PIL import Image
# import os
# from typing import Optional
# import argparse

# def crop_tree_image(img_path: str, output_path: Optional[str] = None):
#     top_trim    = 90
#     right_trim  = 25
#     bottom_trim = 45
#     left_trim   = 5

#     img = Image.open(img_path)
#     w, h = img.size

#     # (left, upper, right, lower)
#     box = (left_trim, top_trim, w - right_trim, h - bottom_trim)

#     cropped = img.crop(box)

#     if output_path is None:
#         output_path = img_path.replace(".png", "-cropped.png")
#         cropped.save(output_path)
#         os.rename(output_path, img_path)
#         return img_path
#     else:
#         cropped.save(output_path)
#         return output_path

# def parse_args():
#     parser = argparse.ArgumentParser(description="Crop a tree image")
#     parser.add_argument("img_path", metavar="IMG_PATH", type=str, help="the path to the image to crop")
#     parser.add_argument("--output-path", metavar="OUTPUT", default=None, type=str, help="where to write output, or omit for in-place")
#     return parser.parse_args()

# def main():
#     args = parse_args()
#     cropped_file_path = crop_tree_image(args.img_path, args.output_path)
#     print(f"Cropped image saved to: {cropped_file_path}")

# if __name__ == "__main__":
#     main()
