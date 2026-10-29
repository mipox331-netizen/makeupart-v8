from pathlib import Path

import cv2
import numpy as np
import pytest

from app.services.photo_finish import apply_photo_finish


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


def test_unknown_photo_finish_is_rejected(tmp_path: Path):
    path = tmp_path / "source.png"
    assert cv2.imwrite(str(path), np.full((16, 16, 3), 100, dtype=np.uint8))

    with pytest.raises(ValueError, match="Unsupported photo finish"):
        apply_photo_finish(path, "AI hairstyle")
