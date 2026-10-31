from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from sqlalchemy.orm import Session

from app.core.config import settings

from app.models.salon import Salon
from app.models.watermark import Watermark


_ALLOWED_POSITIONS = {"bottom-right", "bottom-left", "top-right", "top-left"}


def salon_logo_path(salon_id: str) -> Path:
    """Return a tenant-scoped logo path, rejecting symlink escapes."""
    root = settings.media_root_path.resolve()
    salons_dir = root / "salons"
    salon_dir = salons_dir / str(salon_id)
    branding_dir = salon_dir / "branding"
    target = branding_dir / "logo.png"

    if any(path.is_symlink() for path in (salons_dir, salon_dir, branding_dir, target)):
        raise ValueError("Salon logo storage path failed tenant-isolation validation.")
    try:
        branding_dir.resolve().relative_to(root)
    except ValueError as exc:
        raise ValueError("Salon logo storage path is outside the private media root.") from exc
    return target


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
    content_mode = getattr(watermark, "content_mode", None) or "both"

    # Preserve the historic salon-name watermark by default, while allowing an
    # owner to replace it with their own short brand text.
    if content_mode in {"text", "both"}:
        custom_text = " ".join((getattr(watermark, "watermark_text", None) or "").split())
        name = custom_text or salon.name.strip()
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

    mode = getattr(watermark, "content_mode", None) or "both"
    if mode not in {"text", "logo", "both"}:
        mode = "both"
    lines = _watermark_lines(salon, watermark)
    draw_logo = mode in {"logo", "both"} and bool(watermark.logo_url)
    logo_path = salon_logo_path(str(salon.id)) if draw_logo else None
    logo_available = logo_path is not None and logo_path.is_file()

    if mode == "logo" and not logo_available:
        raise ValueError("Logo-only watermark requires an available salon logo.")
    if not lines and not logo_available:
        return False

    height, width = image.shape[:2]
    margin = max(12, int(round(min(width, height) * 0.02)))
    position = (watermark.position or "bottom-right").strip().lower()
    if position not in _ALLOWED_POSITIONS:
        position = "bottom-right"

    if lines:
        scale = float(np.clip(float(watermark.size) / 18.0, 0.45, 2.0))
        thickness = max(1, int(round(scale * 1.5)))
        padding = max(10, int(round(scale * 12)))
        line_gap = max(6, int(round(scale * 10)))
        text_sizes = [
            cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)[0]
            for line in lines
        ]
        box_width = max(size[0] for size in text_sizes) + padding * 2
        box_height = (
            sum(size[1] for size in text_sizes)
            + line_gap * (len(text_sizes) - 1)
            + padding * 2
        )

        x1 = width - box_width - margin if position.endswith("right") else margin
        y1 = height - box_height - margin if position.startswith("bottom") else margin
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
    else:
        # Stable anchor for logo-only placement without drawing an empty panel.
        x1 = margin
        y1 = margin if position.startswith("top") else height - margin
        box_height = 0

    # Compose the salon's uploaded transparent logo onto every generated image.
    # The actual file path is derived from the authenticated salon id, never from
    # a client-controlled URL or path stored in the database.
    if logo_available and logo_path is not None:
        logo = cv2.imread(str(logo_path), cv2.IMREAD_UNCHANGED)
        if logo is not None:
            if logo.ndim == 2:
                logo = cv2.cvtColor(logo, cv2.COLOR_GRAY2BGRA)
            elif logo.shape[2] == 3:
                logo = cv2.cvtColor(logo, cv2.COLOR_BGR2BGRA)

            if logo.shape[2] == 4:
                logo_height = max(
                    32,
                    min(180, int(min(width, height) * float(watermark.size) / 100.0)),
                )
                logo_width = max(
                    1,
                    int(round(logo.shape[1] * logo_height / logo.shape[0])),
                )
                if logo_width > width - 2 * margin:
                    logo_width = width - 2 * margin
                    logo_height = max(1, int(round(logo.shape[0] * logo_width / logo.shape[1])))
                if logo_height > height - 2 * margin:
                    logo_height = height - 2 * margin
                    logo_width = max(1, int(round(logo.shape[1] * logo_height / logo.shape[0])))

                if logo_width > 0 and logo_height > 0:
                    logo = cv2.resize(
                        logo,
                        (logo_width, logo_height),
                        interpolation=cv2.INTER_AREA,
                    )
                    logo_x = margin if position.endswith("left") else width - logo_width - margin
                    if position.startswith("bottom"):
                        logo_y = max(margin, y1 - logo_height - margin // 2)
                    else:
                        logo_y = min(height - logo_height - margin, y1 + box_height + margin // 2)
                    logo_x = max(0, min(logo_x, width - logo_width))
                    logo_y = max(0, min(logo_y, height - logo_height))

                    roi = image[logo_y:logo_y + logo_height, logo_x:logo_x + logo_width]
                    logo_rgb = logo[:, :, :3].astype(np.float32)
                    logo_alpha = (
                        logo[:, :, 3].astype(np.float32) / 255.0
                        * float(np.clip(float(watermark.opacity), 0.0, 1.0))
                    )[:, :, None]
                    image[logo_y:logo_y + logo_height, logo_x:logo_x + logo_width] = (
                        logo_rgb * logo_alpha + roi.astype(np.float32) * (1.0 - logo_alpha)
                    ).clip(0, 255).astype(np.uint8)

    if not cv2.imwrite(str(path), image):
        raise OSError("Could not save watermarked image")

    return True
