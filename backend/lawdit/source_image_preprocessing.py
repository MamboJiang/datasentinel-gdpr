"""Temporary OCR image candidate generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from PIL import Image
except Exception:  # pragma: no cover - optional OCR enhancement dependency
    Image = None  # type: ignore[assignment]


def ocr_candidate_images(image_path: Path, directory: Path) -> tuple[Path, ...]:
    candidates = [image_path]
    normalized = _normalized_png(image_path, directory)
    if normalized:
        candidates.append(normalized)
    candidates.extend(_preprocessed_overlay_images(image_path, directory))
    return tuple(candidates)


def _normalized_png(image_path: Path, directory: Path) -> Path | None:
    if Image is None or image_path.suffix.lower() == ".png":
        return None
    try:
        image = Image.open(image_path)
        output = _rgb_image(image)
    except Exception:
        return None
    output_path = directory / "source_normalized.png"
    output.save(output_path, format="PNG")
    return output_path


def _rgb_image(image: Any) -> Any:
    if image.mode in {"RGBA", "LA"} or "transparency" in image.info:
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, "white")
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    return image.convert("RGB")


def _preprocessed_overlay_images(image_path: Path, directory: Path) -> tuple[Path, ...]:
    if Image is None:
        return ()
    try:
        image = Image.open(image_path).convert("RGB")
    except Exception:
        return ()
    candidates: list[Path] = []
    red_path = directory / "source_red_overlay.png"
    if _write_mask_variant(image, red_path, "red"):
        candidates.append(red_path)
    saturated_path = directory / "source_saturated_overlay.png"
    if _write_mask_variant(image, saturated_path, "saturated"):
        candidates.append(saturated_path)
    return tuple(candidates)


def _write_mask_variant(image: Any, path: Path, mode: str) -> bool:
    width, height = image.size
    total = width * height
    output = []
    selected = 0
    min_x, min_y, max_x, max_y = width, height, -1, -1
    if mode == "saturated":
        pixels = image.convert("HSV").getdata()
        for index, (_hue, saturation, value) in enumerate(pixels):
            foreground = saturation > 90 and value > 80
            if foreground:
                selected += 1
                x, y = index % width, index // width
                min_x, min_y = min(min_x, x), min(min_y, y)
                max_x, max_y = max(max_x, x), max(max_y, y)
            output.append(0 if foreground else 255)
    else:
        for index, (red, green, blue) in enumerate(image.getdata()):
            foreground = red > 120 and red > green + 35 and red > blue + 35
            if foreground:
                selected += 1
                x, y = index % width, index // width
                min_x, min_y = min(min_x, x), min(min_y, y)
                max_x, max_y = max(max_x, x), max(max_y, y)
            output.append(0 if foreground else 255)
    ratio = selected / total if total else 0
    if selected < 24 or ratio > 0.35:
        return False
    mask = Image.new("L", image.size, 255)
    mask.putdata(output)
    mask = _crop_and_scale_mask(mask, (min_x, min_y, max_x + 1, max_y + 1))
    mask.save(path)
    return True


def _crop_and_scale_mask(mask: Any, bbox: tuple[int, int, int, int]) -> Any:
    width, height = mask.size
    left, top, right, bottom = bbox
    margin = max(24, min(width, height) // 80)
    left = max(0, left - margin)
    top = max(0, top - margin)
    right = min(width, right + margin)
    bottom = min(height, bottom + margin)
    if left < right and top < bottom:
        mask = mask.crop((left, top, right, bottom))

    max_side = max(mask.size)
    if max_side and max_side < 1600:
        scale = 2 if max_side >= 800 else 3
        resampling = getattr(getattr(Image, "Resampling", Image), "NEAREST", 0)
        mask = mask.resize((mask.size[0] * scale, mask.size[1] * scale), resampling)
    return mask
