from pathlib import Path

import cv2
import numpy as np


PHOTO_FINISH_MATRICES: dict[str, tuple[np.ndarray, np.ndarray]] = {
    "Natural Finish": (np.eye(3, dtype=np.float32), np.zeros(3, dtype=np.float32)),
    "Warm Glow": (
        np.array([[0.96, 0.0, 0.0], [0.0, 1.01, 0.0], [0.0, 0.0, 1.04]], dtype=np.float32),
        np.array([-3.0, 1.0, 4.0], dtype=np.float32),
    ),
    "Soft Glam": (
        np.array([[1.02, 0.005, 0.0], [0.005, 1.035, 0.0], [0.0, 0.01, 1.05]], dtype=np.float32),
        np.array([2.0, 3.0, 4.0], dtype=np.float32),
    ),
    "Studio Polish": (
        np.array([[0.94, 0.04, 0.02], [0.03, 0.94, 0.03], [0.02, 0.04, 0.94]], dtype=np.float32),
        np.array([5.0, 5.0, 5.0], dtype=np.float32),
    ),
    "Golden Hour": (
        np.array([[0.90, 0.005, 0.0], [0.01, 1.025, 0.0], [0.0, 0.01, 1.08]], dtype=np.float32),
        np.array([-5.0, 2.0, 5.0], dtype=np.float32),
    ),
}


def apply_photo_finish(image_path: str | Path, finish: str) -> bool:
    """Apply a validated deterministic color grade to a server-owned result image."""
    if finish not in PHOTO_FINISH_MATRICES:
        raise ValueError("Unsupported photo finish")

    path = Path(image_path).expanduser().resolve()
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Could not load processed image for photo finishing")

    if finish == "Natural Finish":
        return False

    matrix, bias = PHOTO_FINISH_MATRICES[finish]
    transformed = cv2.transform(image.astype(np.float32), matrix)
    transformed += bias.reshape((1, 1, 3))
    transformed = np.clip(transformed, 0, 255).astype(np.uint8)

    temporary = path.with_name(f".{path.stem}.finished{path.suffix}")
    try:
        if not cv2.imwrite(str(temporary), transformed):
            raise OSError("Could not encode photo finish")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)

    return True


def apply_photo_adjustments(
    image_path: str | Path,
    *,
    brightness: float = 0.0,
    contrast: float = 1.0,
    saturation: float = 1.0,
    warmth: float = 0.0,
    sharpness: float = 0.0,
) -> bool:
    """Apply non-generative, deterministic photo adjustments to a server-owned image.

    Values are normalized and deliberately bounded so a single control cannot
    destroy the photo. The default values preserve the image byte-for-byte at
    the pixel level; this operation never changes image dimensions.
    """
    values = {
        "brightness": (brightness, -0.25, 0.25),
        "contrast": (contrast, 0.5, 1.5),
        "saturation": (saturation, 0.0, 2.0),
        "warmth": (warmth, -0.25, 0.25),
        "sharpness": (sharpness, 0.0, 1.0),
    }
    normalized: dict[str, float] = {}
    for name, (raw, minimum, maximum) in values.items():
        value = float(raw)
        if not np.isfinite(value) or value < minimum or value > maximum:
            raise ValueError(f"Unsupported {name} adjustment")
        normalized[name] = value

    if (
        normalized["brightness"] == 0.0
        and normalized["contrast"] == 1.0
        and normalized["saturation"] == 1.0
        and normalized["warmth"] == 0.0
        and normalized["sharpness"] == 0.0
    ):
        return False

    path = Path(image_path).expanduser().resolve()
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Could not load image for photo adjustments")

    adjusted = image.astype(np.float32)
    adjusted = (
        (adjusted - 127.5) * normalized["contrast"]
        + 127.5
        + normalized["brightness"] * 255.0
    )
    # OpenCV stores BGR: positive warmth moves red up and blue down.
    adjusted[:, :, 0] -= normalized["warmth"] * 48.0
    adjusted[:, :, 2] += normalized["warmth"] * 48.0
    adjusted = np.clip(adjusted, 0, 255).astype(np.uint8)

    if normalized["saturation"] != 1.0:
        hsv = cv2.cvtColor(adjusted, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 1] = np.clip(
            hsv[:, :, 1] * normalized["saturation"], 0, 255
        )
        adjusted = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    if normalized["sharpness"] > 0.0:
        blurred = cv2.GaussianBlur(adjusted, (0, 0), sigmaX=1.15)
        amount = normalized["sharpness"]
        adjusted = cv2.addWeighted(
            adjusted, 1.0 + amount, blurred, -amount, 0
        )

    temporary = path.with_name(f".{path.stem}.adjusted{path.suffix}")
    try:
        if not cv2.imwrite(str(temporary), adjusted):
            raise OSError("Could not encode adjusted photo")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)

    return True
