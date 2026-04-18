from pathlib import Path

import pytest
from PIL import Image

from app.utils.image_utils import (
    calculate_sha256,
    generate_preview,
    generate_thumbnail,
    get_image_info,
    validate_image,
)


@pytest.fixture
def test_image(tmp_path):
    img = Image.new("RGB", (100, 100), color="red")
    path = tmp_path / "test.jpg"
    img.save(path, "JPEG")
    return str(path)


@pytest.fixture
def large_image(tmp_path):
    img = Image.new("RGB", (3000, 2000), color="blue")
    path = tmp_path / "large.jpg"
    img.save(path, "JPEG")
    return str(path)


@pytest.fixture
def small_image(tmp_path):
    img = Image.new("RGB", (50, 50), color="green")
    path = tmp_path / "small.jpg"
    img.save(path, "JPEG")
    return str(path)


def test_calculate_sha256(test_image):
    result = calculate_sha256(test_image)
    assert len(result) == 64
    assert all(c in "0123456789abcdef" for c in result)


def test_validate_image_valid(test_image):
    assert validate_image(test_image) is True


def test_validate_image_invalid(tmp_path):
    bad_file = tmp_path / "bad.jpg"
    bad_file.write_text("not an image")
    assert validate_image(str(bad_file)) is False


def test_get_image_info(test_image):
    mime, w, h = get_image_info(test_image)
    assert mime == "image/jpeg"
    assert w == 100
    assert h == 100


def test_generate_thumbnail(test_image, tmp_path):
    output = str(tmp_path / "thumb.jpg")
    generate_thumbnail(test_image, output, width=200)
    assert Path(output).exists()
    with Image.open(output) as img:
        assert img.width <= 200


def test_generate_thumbnail_no_upscale(small_image, tmp_path):
    output = str(tmp_path / "thumb.jpg")
    generate_thumbnail(small_image, output, width=200)
    assert Path(output).exists()
    with Image.open(output) as img:
        assert img.width == 50


def test_generate_preview(large_image, tmp_path):
    output = str(tmp_path / "preview.jpg")
    generate_preview(large_image, output, max_width=1920)
    assert Path(output).exists()
    with Image.open(output) as img:
        assert img.width <= 1920


def test_generate_preview_no_upscale(test_image, tmp_path):
    output = str(tmp_path / "preview.jpg")
    generate_preview(test_image, output, max_width=1920)
    assert Path(output).exists()
    with Image.open(output) as img:
        assert img.width == 100
