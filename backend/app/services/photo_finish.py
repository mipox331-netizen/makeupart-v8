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
