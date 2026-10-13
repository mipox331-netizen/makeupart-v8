import os
import tempfile
from pathlib import Path
from typing import Any

import cv2
import numpy as np

try:
    import mediapipe as mp
except ImportError:  # pragma: no cover
    mp = None

class SkinToneMatcher:
    ToneMap = (
        (190, "very-light"),
        (170, "light"),
        (145, "medium"),
        (120, "olive"),
        (95, "deep"),
        (0, "very-deep"),
    )

    @staticmethod
    def _face_sample_mask(image: np.ndarray, landmarks: Any) -> np.ndarray:
        height, width = image.shape[:2]
        points = np.array(
            [[int(point.x * width), int(point.y * height)] for point in landmarks.landmark],
            dtype=np.int32,
        )
        hull = cv2.convexHull(points)
        face_mask = np.zeros((height, width), dtype=np.uint8)
        cv2.fillConvexPoly(face_mask, hull, 255)

        x, y, w, h = cv2.boundingRect(hull)
        inner = np.zeros((height, width), dtype=np.uint8)
        center = (x + w // 2, y + int(h * 0.56))
        axes = (max(1, int(w * 0.38)), max(1, int(h * 0.34)))
        cv2.ellipse(inner, center, axes, 0, 0, 360, 255, -1)

        return cv2.bitwise_and(face_mask, inner)

    @staticmethod
    def _skin_candidate_mask(image: np.ndarray, face_mask: np.ndarray) -> np.ndarray:
        ycrcb = cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)
        y_channel, cr, cb = cv2.split(ycrcb)
        blue, green, red = cv2.split(image)

        color_mask = (
            (y_channel > 35)
            & (cr >= 125)
            & (cr <= 195)
            & (cb >= 65)
            & (cb <= 145)
            & (red >= green * 0.82)
            & (red >= blue * 0.92)
        )
        return (color_mask.astype(np.uint8) * 255) & face_mask

    @classmethod
    def _sample_pixels(cls, image: np.ndarray, landmarks: Any) -> np.ndarray:
        face_mask = cls._face_sample_mask(image, landmarks)
        candidate_mask = cls._skin_candidate_mask(image, face_mask)

        if int(np.count_nonzero(candidate_mask)) < 200:
            candidate_mask = face_mask

        pixels = image[candidate_mask > 0]
        if pixels.size == 0:
            raise ValueError("Could not estimate skin tone from the detected face")
        return pixels

    @classmethod
    def detect(cls, image: np.ndarray, landmarks: Any) -> dict[str, str]:
        pixels = cls._sample_pixels(image, landmarks)
        sample = pixels.reshape(-1, 1, 3).astype(np.uint8)
        lab = cv2.cvtColor(sample, cv2.COLOR_BGR2LAB).reshape(-1, 3)

        lightness = float(np.median(lab[:, 0]))
        a_channel = float(np.median(lab[:, 1])) - 128.0
        b_channel = float(np.median(lab[:, 2])) - 128.0

        tone = next(name for threshold, name in cls.ToneMap if lightness >= threshold)
        delta = b_channel - a_channel
        if delta >= 4.0:
            undertone = "warm"
        elif delta <= -4.0:
            undertone = "cool"
        else:
            undertone = "neutral"
        return {"tone": tone, "undertone": undertone}

    def recommend_foundation(self, skin_tone: str, undertone: str) -> str:
        return f"{skin_tone}-{undertone}"


class BeautyProvider:
    _face_mesh: Any | None = None

    @classmethod
    def _face_mesh_available(cls):
        if mp is None:
            return False
        try:
            return hasattr(mp, "solutions") and hasattr(mp.solutions, "face_mesh")
        except Exception:
            return False

    @classmethod
    def _get_face_mesh(cls):
        if not cls._face_mesh_available():
            raise RuntimeError("mediapipe is not installed")
        if cls._face_mesh is None:
            cls._face_mesh = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=True,
                max_num_faces=2,
                refine_landmarks=True,
            )
        return cls._face_mesh

    def is_ready(self) -> bool:
        try:
            self._get_face_mesh()
            return True
        except Exception:
            return False

    @staticmethod
    def _enhance_skin(image: np.ndarray, landmarks: Any, intensity: float) -> np.ndarray:
        height, width = image.shape[:2]
        points = np.array(
            [[int(point.x * width), int(point.y * height)] for point in landmarks.landmark],
            dtype=np.int32,
        )
        face_hull = cv2.convexHull(points)
        mask = np.zeros((height, width), dtype=np.uint8)
        cv2.fillConvexPoly(mask, face_hull, 255)
        mask = cv2.GaussianBlur(mask, (0, 0), sigmaX=max(1.0, width / 120))
        blend = (mask.astype(np.float32) / 255.0 * 0.18 * intensity)[..., None]
        smoothed = cv2.bilateralFilter(
            image,
            d=0,
            sigmaColor=20 + 40 * intensity,
            sigmaSpace=10 + 20 * intensity,
        )
        return np.clip(image * (1 - blend) + smoothed * blend, 0, 255).astype(np.uint8)

    @staticmethod
    def _apply_makeup(
        image: np.ndarray,
        landmarks: Any,
        makeup_style: str,
        intensity: float,
    ) -> np.ndarray:
        """Apply face-mesh-guided lipstick, blush, eyeshadow and eyeliner.

        This is a lightweight OpenCV cosmetic overlay, not a generative model:
        it preserves the source pixels outside the local makeup masks and does
        not synthesize hairstyles. The API validates the style before this call.
        """
        palettes = {
            "natural": {
                "lip": (112, 78, 174),
                "lip_alpha": 0.18,
                "blush": (132, 92, 190),
                "blush_alpha": 0.055,
                "eye_shadow": (128, 108, 153),
                "eye_shadow_alpha": 0.025,
                "liner_alpha": 0.06,
            },
            "soft_glam": {
                "lip": (86, 54, 197),
                "lip_alpha": 0.34,
                "blush": (144, 88, 218),
                "blush_alpha": 0.115,
                "eye_shadow": (100, 70, 170),
                "eye_shadow_alpha": 0.105,
                "liner_alpha": 0.48,
            },
            "bridal_rose": {
                "lip": (116, 82, 211),
                "lip_alpha": 0.30,
                "blush": (153, 105, 224),
                "blush_alpha": 0.14,
                "eye_shadow": (126, 94, 190),
                "eye_shadow_alpha": 0.075,
                "liner_alpha": 0.32,
            },
            "evening_glam": {
                "lip": (48, 29, 160),
                "lip_alpha": 0.48,
                "blush": (128, 72, 190),
                "blush_alpha": 0.10,
                "eye_shadow": (48, 38, 92),
                "eye_shadow_alpha": 0.19,
                "liner_alpha": 0.72,
            },
        }
        palette = palettes.get(makeup_style)
        if palette is None or intensity <= 0:
            return image

        # MediaPipe Face Mesh lip boundary. The inner-mouth polygon is excluded
        # so the tint follows the lips rather than painting teeth or the mouth.
        outer_lip = (
            61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291,
            308, 324, 318, 402, 317, 14, 87, 178, 88, 95, 78,
        )
        inner_mouth = (78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308)
        points = np.array(
            [
                [
                    max(0, min(image.shape[1] - 1, int(round(point.x * (image.shape[1] - 1))))),
                    max(0, min(image.shape[0] - 1, int(round(point.y * (image.shape[0] - 1))))),
                ]
                for point in landmarks.landmark
            ],
            dtype=np.int32,
        )
        required_index = max(max(outer_lip), max(inner_mouth))
        if len(points) <= required_index:
            # Some legacy tests and custom providers return partial landmarks.
            return image

        height, width = image.shape[:2]
        face_hull = cv2.convexHull(points)
        face_mask = np.zeros((height, width), dtype=np.uint8)
        cv2.fillConvexPoly(face_mask, face_hull, 255)
        x, y, w, h = cv2.boundingRect(face_hull)
        if w < 12 or h < 12:
            return image

        styled = image.astype(np.float32)

        cheek_mask = np.zeros((height, width), dtype=np.uint8)
        cheek_axes = (max(3, int(w * 0.095)), max(2, int(h * 0.032)))
        cheek_y = y + int(h * 0.63)
        cv2.ellipse(
            cheek_mask,
            (x + int(w * 0.32), cheek_y),
            cheek_axes,
            -8,
            0,
            360,
            255,
            -1,
        )
        cv2.ellipse(
            cheek_mask,
            (x + int(w * 0.68), cheek_y),
            cheek_axes,
            8,
            0,
            360,
            255,
            -1,
        )
        cheek_mask = cv2.bitwise_and(cheek_mask, face_mask)
        cheek_mask = cv2.GaussianBlur(
            cheek_mask,
            (0, 0),
            sigmaX=max(1.0, width / 55.0),
        )
        cheek_alpha = (
            cheek_mask.astype(np.float32) / 255.0
            * float(palette["blush_alpha"])
            * float(np.clip(intensity, 0.0, 1.0))
        )[:, :, None]
        blush = np.asarray(palette["blush"], dtype=np.float32)[None, None, :]
        styled = styled * (1.0 - cheek_alpha) + blush * cheek_alpha

        lip_mask = np.zeros((height, width), dtype=np.uint8)
        cv2.fillPoly(lip_mask, [points[list(outer_lip)]], 255)
        cv2.fillPoly(lip_mask, [points[list(inner_mouth)]], 0)
        lip_mask = cv2.GaussianBlur(
            lip_mask,
            (0, 0),
            sigmaX=max(0.8, width / 420.0),
        )
        lip_alpha = (
            lip_mask.astype(np.float32) / 255.0
            * float(palette["lip_alpha"])
            * float(np.clip(intensity, 0.0, 1.0))
        )[:, :, None]
        lip_color = np.asarray(palette["lip"], dtype=np.float32)[None, None, :]
        styled = styled * (1.0 - lip_alpha) + lip_color * lip_alpha

        # Shade the upper eyelids from MediaPipe Face Mesh contours. These
        # indices exist in the refined 478-point mesh; partial legacy fixtures
        # keep the older lip/blush behavior without risking an index error.
        upper_eye_paths = (
            (33, 246, 161, 160, 159, 158, 157, 173, 133),
            (263, 466, 388, 387, 386, 385, 384, 398, 362),
        )
        if len(points) > 466:
            clipped_intensity = float(np.clip(intensity, 0.0, 1.0))
            shadow_height = max(2, int(h * 0.035))
            shadow_color = np.asarray(
                palette.get("eye_shadow", palette["lip"]), dtype=np.float32
            )[None, None, :]
            shadow_strength = float(palette.get("eye_shadow_alpha", 0.0))
            liner_color = np.asarray((22, 18, 30), dtype=np.float32)[None, None, :]
            liner_strength = float(palette.get("liner_alpha", 0.0))
            liner_width = max(1, int(round(w * 0.005)))

            for contour in upper_eye_paths:
                upper = points[list(contour)].copy()
                shifted = upper.copy()
                shifted[:, 1] = np.maximum(0, shifted[:, 1] - shadow_height)
                shadow_polygon = np.vstack((upper, shifted[::-1]))
                shadow_mask = np.zeros((height, width), dtype=np.uint8)
                cv2.fillPoly(shadow_mask, [shadow_polygon], 255)
                shadow_mask = cv2.bitwise_and(shadow_mask, face_mask)
                shadow_mask = cv2.GaussianBlur(
                    shadow_mask, (0, 0), sigmaX=max(1.0, width / 150.0)
                )
                shadow_alpha = (
                    shadow_mask.astype(np.float32) / 255.0
                    * shadow_strength
                    * clipped_intensity
                )[:, :, None]
                styled = styled * (1.0 - shadow_alpha) + shadow_color * shadow_alpha

                # A narrow anti-aliased line follows the upper lash line and a
                # small outward wing. It is intentionally lighter in natural
                # and bridal looks than in soft/evening glam.
                outer_index = contour[0]
                outer = points[outer_index]
                direction = -1 if outer[0] < (x + w // 2) else 1
                wing = np.array(
                    [
                        max(0, min(width - 1, int(outer[0] + direction * max(2, int(w * 0.022))))),
                        max(0, int(outer[1] - max(1, int(h * 0.008)))),
                    ],
                    dtype=np.int32,
                )
                liner_path = np.vstack((wing, upper))
                liner_mask = np.zeros((height, width), dtype=np.uint8)
                cv2.polylines(
                    liner_mask,
                    [liner_path],
                    isClosed=False,
                    color=255,
                    thickness=liner_width,
                    lineType=cv2.LINE_AA,
                )
                liner_alpha = (
                    liner_mask.astype(np.float32) / 255.0
                    * liner_strength
                    * clipped_intensity
                )[:, :, None]
                styled = styled * (1.0 - liner_alpha) + liner_color * liner_alpha

        return np.clip(styled, 0, 255).astype(np.uint8)

    def process(self, image_path: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = options or {}
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not decode image: {image_path}")
        if not self._face_mesh_available():
            raise RuntimeError("MediaPipe Face Mesh is unavailable")

        face_mesh = self._get_face_mesh()
        face_mesh_result = face_mesh.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        landmarks = face_mesh_result.multi_face_landmarks or []
        if not landmarks:
            raise ValueError("No face detected in the provided image")
        if len(landmarks) != 1:
            raise ValueError("Please upload a photo containing exactly one face")

        skin_matcher = SkinToneMatcher()
        tone = skin_matcher.detect(image, landmarks[0])
        intensity = float(payload.get("intensity", 0.7))
        processed = self._enhance_skin(image, landmarks[0], intensity)
        # Measure structural preservation before cosmetic color overlays; the
        # metric is not biometric identity recognition and should not reject a
        # deliberate lip/cheek color change as if it distorted facial geometry.
        similarity = IdentityGuard.measure_similarity(image, processed, landmarks[0])
        makeup_style = str(payload.get("makeup_style", "natural"))
        processed = self._apply_makeup(processed, landmarks[0], makeup_style, intensity)

        output_dir = payload.get("output_dir")
        if output_dir:
            output_path = Path(str(output_dir)).expanduser().resolve()
            output_path.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=output_path, suffix=".png", delete=False) as tmp_file:
                saved_path = tmp_file.name
        else:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
                saved_path = tmp_file.name
        if not cv2.imwrite(saved_path, processed):
            os.unlink(saved_path)
            raise OSError("Could not write the processed image")

        return {
            "identity_similarity": round(similarity, 4),
            "skin_tone": tone["tone"],
            "undertone": tone["undertone"],
            "foundation_match": skin_matcher.recommend_foundation(
                tone["tone"], tone["undertone"]
            ),
            "processed": True,
            "output_path": saved_path,
        }


class IdentityGuard:
    """Bounds how much the non-generative skin-smoothing filter changes the face image.

    The score measures structural image preservation, not biometric identity, and is
    not proof of identity for arbitrary or AI-generated images. The old API field
    name is retained for mobile-client compatibility.
    """

    min_similarity = 0.85

    @staticmethod
    def measure_similarity(
        original: np.ndarray,
        processed: np.ndarray,
        landmarks: Any,
    ) -> float:
        if (
            original.ndim != 3
            or processed.ndim != 3
            or original.shape != processed.shape
            or original.size == 0
        ):
            return 0.0

        mask = SkinToneMatcher._face_sample_mask(original, landmarks) > 0
        if int(np.count_nonzero(mask)) < 16:
            return 0.0

        original_gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY).astype(np.float32)
        processed_gray = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY).astype(np.float32)

        # SSIM-style local statistics; no pretrained face-recognition model is loaded.
        mu_original = cv2.GaussianBlur(original_gray, (11, 11), 1.5)
        mu_processed = cv2.GaussianBlur(processed_gray, (11, 11), 1.5)
        original_sq = original_gray * original_gray
        processed_sq = processed_gray * processed_gray
        cross = original_gray * processed_gray
        variance_original = cv2.GaussianBlur(original_sq, (11, 11), 1.5) - mu_original * mu_original
        variance_processed = cv2.GaussianBlur(processed_sq, (11, 11), 1.5) - mu_processed * mu_processed
        covariance = cv2.GaussianBlur(cross, (11, 11), 1.5) - mu_original * mu_processed

        c1 = (0.01 * 255.0) ** 2
        c2 = (0.03 * 255.0) ** 2
        numerator = (2.0 * mu_original * mu_processed + c1) * (2.0 * covariance + c2)
        denominator = (
            (mu_original * mu_original + mu_processed * mu_processed + c1)
            * (variance_original + variance_processed + c2)
        )
        score_map = numerator / np.maximum(denominator, 1e-12)
        scores = score_map[mask]
        if scores.size == 0 or not np.isfinite(scores).all():
            return 0.0
        return float(np.clip(np.mean(scores), 0.0, 1.0))

    def validate(self, similarity: float, intensity: float) -> tuple[float, bool]:
        current_intensity = max(0.0, min(1.0, intensity))
        return current_intensity, float(similarity) >= self.min_similarity
