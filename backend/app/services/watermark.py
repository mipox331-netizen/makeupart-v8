from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from sqlalchemy.orm import Session

from app.models.salon import Salon
from app.models.watermark import Watermark


_ALLOWED_POSITIONS = {"bottom-right", "bottom-left", "top-right", "top-left"}


def get_or_create_watermark(db: Session, salon: Salon) -> Watermark:
    watermark = (
        db.query(Watermark)
        .filter(Watermark.salon_id == salon.id)
        .one_or_none()
    )
    if watermark is not None:
        return watermark

    watermark = Watermark(
        salon_id=salon.id,
        logo_url=salon.logo_url,
        salon_name=True,
        phone=False,
        instagram=False,
        tiktok=False,
        position="bottom-right",
        opacity=0.5,
        size=12,
    )
    db.add(watermark)
    db.flush()
    return watermark


def _watermark_lines(salon: Salon, watermark: Watermark) -> list[str]:
    lines: list[str] = []

    # Enforce salon branding even if a legacy row stores salon_name=False.
    name = salon.name.strip()
    if name:
        lines.append(name)

    if watermark.phone and salon.phone:
        lines.append(salon.phone.strip())

    if watermark.instagram and salon.instagram:
        handle = salon.instagram.strip()
        if handle and not handle.startswith("@"):
            handle = f"@{handle}"
        lines.append(handle)

    if watermark.tiktok and salon.tiktok:
        handle = salon.tiktok.strip()
        if handle and not handle.startswith("@"):
            handle = f"@{handle}"
        lines.append(handle)

    return [line for line in lines if line]


def apply_watermark(
    image_path: str | Path,
    salon: Salon,
    watermark: Watermark,
) -> bool:
    path = Path(image_path).expanduser().resolve()
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Could not load processed image for watermarking")

    lines = _watermark_lines(salon, watermark)
    if not lines:
        return False

    height, width = image.shape[:2]
    scale = float(np.clip(float(watermark.size) / 18.0, 0.45, 2.0))
    thickness = max(1, int(round(scale * 1.5)))
    padding = max(10, int(round(scale * 12)))
    line_gap = max(6, int(round(scale * 10)))

    text_sizes = [
        cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)[0]
        for line in lines
    ]
    box_width = max(size[0] for size in text_sizes) + padding * 2
    box_height = sum(size[1] for size in text_sizes) + line_gap * (len(lines) - 1) + padding * 2

    margin = max(12, int(round(min(width, height) * 0.02)))
    position = (watermark.position or "bottom-right").strip().lower()
    if position not in _ALLOWED_POSITIONS:
        position = "bottom-right"

    if position.endswith("right"):
        x1 = width - box_width - margin
    else:
        x1 = margin

    if position.startswith("bottom"):
        y1 = height - box_height - margin
    else:
        y1 = margin

    x1 = max(margin, min(x1, max(margin, width - box_width - margin)))
    y1 = max(margin, min(y1, max(margin, height - box_height - margin)))
    x2 = min(width - margin, x1 + box_width)
    y2 = min(height - margin, y1 + box_height)

    alpha = float(np.clip(float(watermark.opacity), 0.0, 1.0))
    overlay = image.copy()
    cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 0, 0), thickness=-1)
    image = cv2.addWeighted(overlay, alpha, image, 1.0 - alpha, 0.0)

    baseline_y = y1 + padding + text_sizes[0][1]
    for index, line in enumerate(lines):
        if index > 0:
            baseline_y += line_gap + text_sizes[index][1]
        cv2.putText(
            image,
            line,
            (x1 + padding, baseline_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            scale,
            (255, 255, 255),
            thickness,
            cv2.LINE_AA,
        )

    if not cv2.imwrite(str(path), image):
        raise OSError("Could not save watermarked image")

    return True
