from pathlib import Path

import cv2
import numpy as np
import pytest

from app.services.photo_finish import apply_photo_adjustments, apply_photo_finish


def test_natural_finish_preserves_original_pixels(tmp_path: Path):
    path = tmp_path / "natural.png"
    source = np.full((64, 64, 3), 120, dtype=np.uint8)
    assert cv2.imwrite(str(path), source)

    applied = apply_photo_finish(path, "Natural Finish")
    output = cv2.imread(str(path), cv2.IMREAD_COLOR)

    assert applied is False
    assert output is not None
    assert np.array_equal(output, source)


@pytest.mark.parametrize("finish", ["Warm Glow", "Soft Glam", "Studio Polish", "Golden Hour"])
def test_photo_finish_changes_pixels_and_keeps_dimensions(tmp_path: Path, finish: str):
    path = tmp_path / "styled.png"
    source = np.full((80, 96, 3), 120, dtype=np.uint8)
    assert cv2.imwrite(str(path), source)

    applied = apply_photo_finish(path, finish)
    output = cv2.imread(str(path), cv2.IMREAD_COLOR)

    assert applied is True
    assert output is not None
    assert output.shape == source.shape
    assert not np.array_equal(output, source)


def test_default_photo_adjustments_preserve_original_pixels(tmp_path: Path):
    path = tmp_path / "adjustments-default.png"
    source = np.arange(80 * 96 * 3, dtype=np.uint8).reshape((80, 96, 3))
    assert cv2.imwrite(str(path), source)

    applied = apply_photo_adjustments(path)
    output = cv2.imread(str(path), cv2.IMREAD_COLOR)

    assert applied is False
    assert output is not None
    assert np.array_equal(output, source)


@pytest.mark.parametrize(
    "options",
    [
        {"brightness": 0.12},
        {"contrast": 1.25},
        {"saturation": 1.6},
        {"warmth": 0.2},
        {"sharpness": 0.75},
        {
            "brightness": 0.08,
            "contrast": 1.1,
            "saturation": 1.2,
            "warmth": 0.12,
            "sharpness": 0.3,
        },
    ],
)
def test_manual_photo_adjustments_change_pixels_without_resizing(
    tmp_path: Path, options: dict[str, float]
):
    path = tmp_path / "adjusted.png"
    source = np.zeros((80, 96, 3), dtype=np.uint8)
    source[:, :48] = (40, 80, 130)
    source[:, 48:] = (160, 190, 220)
    cv2.circle(source, (48, 40), 15, (255, 30, 90), -1)
    assert cv2.imwrite(str(path), source)

    applied = apply_photo_adjustments(path, **options)
    output = cv2.imread(str(path), cv2.IMREAD_COLOR)

    assert applied is True
    assert output is not None
    assert output.shape == source.shape
    assert not np.array_equal(output, source)


@pytest.mark.parametrize(
    "options",
    [
        {"brightness": 0.26},
        {"contrast": 1.51},
        {"saturation": 2.01},
        {"warmth": -0.26},
        {"sharpness": -0.01},
    ],
)
def test_manual_photo_adjustments_reject_values_outside_safe_bounds(
    tmp_path: Path, options: dict[str, float]
):
    path = tmp_path / "invalid-adjustment.png"
    assert cv2.imwrite(str(path), np.full((16, 16, 3), 100, dtype=np.uint8))

    with pytest.raises(ValueError, match="Unsupported"):
        apply_photo_adjustments(path, **options)


def test_unknown_photo_finish_is_rejected(tmp_path: Path):
    path = tmp_path / "source.png"
    assert cv2.imwrite(str(path), np.full((16, 16, 3), 100, dtype=np.uint8))

    with pytest.raises(ValueError, match="Unsupported photo finish"):
        apply_photo_finish(path, "AI hairstyle")
