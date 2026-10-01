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

try:
    from insightface.app import FaceAnalysis
except ImportError:  # pragma: no cover
    FaceAnalysis = None


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
    _face_app: Any | None = None

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

    @classmethod
    def _get_face_app(cls):
        if FaceAnalysis is None:
            raise RuntimeError("insightface is not installed")
        if cls._face_app is None:
            insightface_root = os.environ.get("INSIGHTFACE_ROOT", os.path.expanduser("~/.insightface"))
            app = FaceAnalysis(name="buffalo_l", root=insightface_root)
            app.prepare(ctx_id=-1, det_size=(640, 640))
            cls._face_app = app
        return cls._face_app

    def is_ready(self) -> bool:
        try:
            self._get_face_mesh()
            self._get_face_app()
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
        face_app = self._get_face_app()
        original_faces = face_app.get(image)
        processed_faces = face_app.get(processed)
        if not original_faces or not processed_faces:
            raise ValueError("InsightFace could not detect a face in the image")
        if len(original_faces) != 1 or len(processed_faces) != 1:
            raise ValueError("Please upload a photo containing exactly one face")

        original_embedding = original_faces[0].embedding.astype(np.float64)
        processed_embedding = processed_faces[0].embedding.astype(np.float64)
        norm_product = float(np.linalg.norm(original_embedding) * np.linalg.norm(processed_embedding))
        similarity = 0.0 if norm_product == 0 else float(np.dot(original_embedding, processed_embedding) / norm_product)
        similarity = float(np.clip(similarity, 0.0, 1.0))

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
    min_similarity = 0.85

    def validate(self, similarity: float, intensity: float) -> tuple[float, bool]:
        current_intensity = max(0.0, min(1.0, intensity))
        return current_intensity, float(similarity) >= self.min_similarity
