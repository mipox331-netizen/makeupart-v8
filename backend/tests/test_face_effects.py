from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from app.services.beauty import BeautyProvider
from app.services.face_effects import FACE_EDIT_OPTIONS, FaceEffects


def _landmarks():
    points = [(0.5, 0.5)] * 478
    coordinates = {
        10: (0.50, 0.16),
        152: (0.50, 0.90),
        234: (0.22, 0.52),
        454: (0.78, 0.52),
        127: (0.28, 0.30),
        356: (0.72, 0.30),
        93: (0.28, 0.66),
        132: (0.33, 0.76),
        58: (0.40, 0.82),
        172: (0.45, 0.86),
        136: (0.48, 0.88),
        150: (0.49, 0.89),
        149: (0.50, 0.90),
        176: (0.52, 0.89),
        148: (0.55, 0.86),
        377: (0.60, 0.82),
        400: (0.67, 0.76),
        378: (0.72, 0.66),
        379: (0.74, 0.61),
        365: (0.70, 0.74),
        397: (0.65, 0.82),
        288: (0.60, 0.84),
        361: (0.67, 0.76),
        323: (0.72, 0.66),
        33: (0.32, 0.43),
        246: (0.35, 0.405),
        161: (0.38, 0.395),
        160: (0.40, 0.388),
        159: (0.42, 0.385),
        158: (0.44, 0.388),
        157: (0.46, 0.395),
        173: (0.47, 0.405),
        133: (0.48, 0.43),
        263: (0.68, 0.43),
        466: (0.65, 0.405),
        388: (0.62, 0.395),
        387: (0.60, 0.388),
        386: (0.58, 0.385),
        385: (0.56, 0.388),
        384: (0.54, 0.395),
        398: (0.53, 0.405),
        362: (0.52, 0.43),
        168: (0.50, 0.49),
        61: (0.41, 0.64),
        146: (0.43, 0.62),
        91: (0.45, 0.615),
        181: (0.47, 0.61),
        84: (0.49, 0.615),
        17: (0.50, 0.62),
        314: (0.52, 0.615),
        405: (0.54, 0.61),
        321: (0.56, 0.615),
        375: (0.58, 0.62),
        291: (0.59, 0.64),
        308: (0.57, 0.655),
        324: (0.55, 0.665),
        318: (0.53, 0.67),
        402: (0.51, 0.675),
        317: (0.50, 0.676),
        14: (0.49, 0.676),
        87: (0.47, 0.67),
        178: (0.45, 0.665),
        88: (0.43, 0.655),
        95: (0.42, 0.65),
        78: (0.41, 0.64),
    }
    for index, point in coordinates.items():
        points[index] = point
    return SimpleNamespace(
        landmark=[SimpleNamespace(x=x, y=y) for x, y in points]
    )


def _portrait():
    image = np.full((256, 256, 3), 180, dtype=np.uint8)
    yy, xx = np.mgrid[0:256, 0:256]
    face = ((xx - 128) / 72) ** 2 + ((yy - 140) / 94) ** 2 <= 1
    image[face] = (105, 145, 190)
    # Dark hair cap sits above the synthetic forehead.
    hair = ((xx - 128) / 82) ** 2 + ((yy - 44) / 50) ** 2 <= 1
    image[hair] = (22, 22, 22)
    # Keep facial detail visible to the local remapping/smoothing operations.
    texture = (
        (xx[105:220, 85:171] + 3 * yy[105:220, 85:171]) % 7
    ).astype(np.uint8)[:, :, None]
    image[105:220, 85:171] += texture * np.array([1, 2, 3], dtype=np.uint8)
    return image


@pytest.mark.parametrize("edit", sorted(FACE_EDIT_OPTIONS - {"none"}))
def test_every_local_face_edit_changes_a_copy_and_preserves_dimensions(edit):
    source = _portrait()
    before = source.copy()

    result = FaceEffects.apply(source, _landmarks(), edit, 0.85)

    assert result.shape == source.shape, edit
    assert result.dtype == np.uint8, edit
    assert not np.array_equal(result, source), edit
    assert np.array_equal(source, before), "the original input must remain unchanged"


def test_none_and_zero_intensity_are_pixel_identical():
    source = _portrait()
    landmarks = _landmarks()

    assert np.array_equal(FaceEffects.apply(source, landmarks, "none", 0.9), source)
    assert np.array_equal(FaceEffects.apply(source, landmarks, "soft_smile", 0.0), source)




def test_beauty_provider_reports_similarity_after_local_face_edit(monkeypatch, tmp_path):
    class FakeFaceMesh:
        def process(self, image):
            return SimpleNamespace(multi_face_landmarks=[_landmarks()])

    fake_mesh = FakeFaceMesh()
    monkeypatch.setattr(
        BeautyProvider,
        "_face_mesh_available",
        classmethod(lambda cls: True),
    )
    monkeypatch.setattr(
        BeautyProvider,
        "_get_face_mesh",
        classmethod(lambda cls: fake_mesh),
    )

    image_path = tmp_path / "source.png"
    assert cv2.imwrite(str(image_path), _portrait())

    result = BeautyProvider().process(
        str(image_path),
        {
            "face_edit": "soft_smile",
            "intensity": 0.85,
            "output_dir": str(tmp_path / "processed"),
        },
    )

    output = cv2.imread(result["output_path"])
    assert output is not None
    assert output.shape == (256, 256, 3)
    assert not np.array_equal(output, cv2.imread(str(image_path)))
    assert 0.0 <= result["identity_similarity"] < 1.0


def test_unknown_face_edit_is_rejected():
    with pytest.raises(ValueError, match="Unsupported face edit"):
        FaceEffects.apply(_portrait(), _landmarks(), "fake_filter", 0.7)


def test_invalid_landmark_mesh_is_rejected():
    partial = SimpleNamespace(landmark=[SimpleNamespace(x=0.5, y=0.5)] * 20)
    with pytest.raises(ValueError, match="complete face mesh"):
        FaceEffects.apply(_portrait(), partial, "soft_smile", 0.7)
