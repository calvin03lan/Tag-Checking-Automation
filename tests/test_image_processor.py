"""Unit tests for utils/image_processor.py"""
import pytest
from pathlib import Path
from PIL import Image

from utils.image_processor import stitch_images


def _solid_image(path: str, w: int, h: int, colour=(200, 100, 50)) -> str:
    Image.new("RGB", (w, h), colour).save(path)
    return path


class TestStitchImages:
    def test_output_file_created(self, tmp_path):
        top    = _solid_image(str(tmp_path / "top.png"),    800, 400)
        bottom = _solid_image(str(tmp_path / "bottom.png"), 600, 300, (0, 0, 255))
        out    = str(tmp_path / "stitched.png")

        result = stitch_images(top, bottom, out, target_width=1280)
        assert Path(result).exists()

    def test_output_width_matches_target(self, tmp_path):
        top    = _solid_image(str(tmp_path / "top.png"),    800, 400)
        bottom = _solid_image(str(tmp_path / "bottom.png"), 600, 300)
        out    = str(tmp_path / "stitched.png")

        stitch_images(top, bottom, out, target_width=960)
        img = Image.open(out)
        assert img.width == 960

    def test_output_height_is_sum_of_scaled_heights(self, tmp_path):
        # Both images are square 400×400; scaled to 800 wide → 800 tall each
        top    = _solid_image(str(tmp_path / "top.png"),    400, 400)
        bottom = _solid_image(str(tmp_path / "bottom.png"), 400, 400)
        out    = str(tmp_path / "stitched.png")

        stitch_images(top, bottom, out, target_width=800)
        img = Image.open(out)
        assert img.height == 1600   # 800 + 800

    def test_returns_absolute_path(self, tmp_path):
        top    = _solid_image(str(tmp_path / "top.png"),    200, 100)
        bottom = _solid_image(str(tmp_path / "bottom.png"), 200, 100)
        out    = str(tmp_path / "out.png")

        result = stitch_images(top, bottom, out)
        assert Path(result).is_absolute()

    def test_missing_top_raises(self, tmp_path):
        bottom = _solid_image(str(tmp_path / "bottom.png"), 200, 100)
        with pytest.raises(FileNotFoundError):
            stitch_images(
                str(tmp_path / "ghost.png"),
                bottom,
                str(tmp_path / "out.png"),
            )

    def test_missing_bottom_raises(self, tmp_path):
        top = _solid_image(str(tmp_path / "top.png"), 200, 100)
        with pytest.raises(FileNotFoundError):
            stitch_images(
                top,
                str(tmp_path / "ghost.png"),
                str(tmp_path / "out.png"),
            )

    def test_creates_parent_output_dir(self, tmp_path):
        top    = _solid_image(str(tmp_path / "top.png"),    200, 100)
        bottom = _solid_image(str(tmp_path / "bottom.png"), 200, 100)
        out    = str(tmp_path / "nested" / "dir" / "out.png")

        stitch_images(top, bottom, out)
        assert Path(out).exists()
