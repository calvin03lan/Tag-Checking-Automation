"""
Image utilities: screenshot capture, vertical stitching, and side-by-side stitching.
No UI or Playwright dependencies.
"""
from pathlib import Path
from typing import Optional

from PIL import Image


def stitch_images(
    top_path: str,
    bottom_path: str,
    output_path: str,
    target_width: int = 1280,
) -> str:
    """
    Vertically concatenate two images and save to *output_path*.

    Both source images are scaled to *target_width* (aspect-ratio preserved)
    before stitching.

    Returns:
        Absolute path of the saved stitched image.

    Raises:
        FileNotFoundError: if either source image is missing.
    """
    for p in (top_path, bottom_path):
        if not Path(p).exists():
            raise FileNotFoundError(f"Image not found: {p}")

    def _resize(img: Image.Image, width: int) -> Image.Image:
        ratio      = width / img.width
        new_height = int(img.height * ratio)
        return img.resize((width, new_height), Image.LANCZOS)

    top    = _resize(Image.open(top_path).convert("RGB"),    target_width)
    bottom = _resize(Image.open(bottom_path).convert("RGB"), target_width)

    canvas = Image.new("RGB", (target_width, top.height + bottom.height))
    canvas.paste(top,    (0, 0))
    canvas.paste(bottom, (0, top.height))

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path)
    return str(Path(output_path).resolve())


def stitch_side_by_side(
    left_path: str,
    right_path: str,
    output_path: str,
) -> str:
    """
    Horizontally concatenate two images and save to *output_path*.

    The left image (GUI screenshot) is placed on the left side and the right
    image (browser screenshot) is placed on the right side.  Both images keep
    their original dimensions; the canvas height equals the taller of the two.

    Returns:
        Absolute path of the saved stitched image.

    Raises:
        FileNotFoundError: if either source image is missing.
    """
    for p in (left_path, right_path):
        if not Path(p).exists():
            raise FileNotFoundError(f"Image not found: {p}")

    left  = Image.open(left_path).convert("RGB")
    right = Image.open(right_path).convert("RGB")

    total_width = left.width + right.width
    max_height  = max(left.height, right.height)

    canvas = Image.new("RGB", (total_width, max_height), (255, 255, 255))
    canvas.paste(left,  (0, 0))
    canvas.paste(right, (left.width, 0))

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path)
    return str(Path(output_path).resolve())


def capture_gui_screenshot(output_path: str) -> Optional[str]:
    """
    Capture the full screen using PIL ImageGrab and save to *output_path*.

    Returns the saved path, or None when ImageGrab is unavailable
    (Linux headless, etc.).
    """
    try:
        from PIL import ImageGrab          # not available on all platforms
        img = ImageGrab.grab()
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path)
        return str(Path(output_path).resolve())
    except (ImportError, OSError):
        return None
