import cv2
import numpy as np

from app.models.salon import Salon
from app.models.watermark import Watermark
from app.services.watermark import apply_watermark
from app.schemas.watermark import WatermarkUpdate
from pydantic import ValidationError
import pytest


def test_apply_watermark_changes_image(tmp_path):
    path = tmp_path / "output.png"
    source = np.full((480, 640, 3), 240, dtype=np.uint8)
    assert cv2.imwrite(str(path), source)

    salon = Salon(name="Tony Beauty Studio")
    watermark = Watermark(
        salon_name=False,
        phone=False,
        instagram=False,
        tiktok=False,
        position="bottom-right",
        opacity=0.5,
        size=12,
    )

    applied = apply_watermark(path, salon, watermark)

    result = cv2.imread(str(path), cv2.IMREAD_COLOR)
    assert applied is True
    assert result is not None
    assert not np.array_equal(source, result)


def test_clients_cannot_disable_required_salon_name():
    with pytest.raises(ValidationError):
        WatermarkUpdate(salon_name=False)
