import hashlib
from pathlib import Path

from PIL import Image


def calculate_sha256(file_path: str) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def validate_image(file_path: str) -> bool:
    try:
        with Image.open(file_path) as img:
            img.verify()
        return True
    except Exception:
        return False


def get_image_info(file_path: str) -> tuple[str, int, int]:
    with Image.open(file_path) as img:
        width, height = img.size
        fmt = img.format or "JPEG"
        mime_map = {
            "JPEG": "image/jpeg",
            "PNG": "image/png",
            "WEBP": "image/webp",
            "BMP": "image/bmp",
            "GIF": "image/gif",
        }
        mime_type = mime_map.get(fmt, "image/jpeg")
        return mime_type, width, height


def generate_thumbnail(
    original_path: str, output_path: str, width: int = 200
) -> None:
    with Image.open(original_path) as img:
        if img.width <= width:
            img.convert("RGB").save(output_path, "JPEG", quality=85)
            return
        ratio = width / img.width
        new_height = int(img.height * ratio)
        resized = img.resize((width, new_height), Image.Resampling.LANCZOS)
        resized.convert("RGB").save(output_path, "JPEG", quality=85)


def generate_preview(
    original_path: str, output_path: str, max_width: int = 1920
) -> None:
    with Image.open(original_path) as img:
        if img.width <= max_width:
            img.convert("RGB").save(output_path, "JPEG", quality=90)
            return
        ratio = max_width / img.width
        new_height = int(img.height * ratio)
        resized = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
        resized.convert("RGB").save(output_path, "JPEG", quality=90)
