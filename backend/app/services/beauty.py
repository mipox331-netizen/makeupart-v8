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
                max_num_faces=1,
                refine_landmarks=True,
            )
        return cls._face_mesh

    @classmethod
    def _get_face_app(cls):
        if FaceAnalysis is None:
            raise RuntimeError("insightface is not installed")
        if cls._face_app is None:
            app = FaceAnalysis(name="buffalo_l", root=os.path.expanduser("~/.insightface"))
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
        if not face_mesh_result.multi_face_landmarks:
            raise ValueError("No face landmarks detected in the provided image")

        intensity = float(payload.get("intensity", 0.7))
        processed = self._enhance_skin(image, face_mesh_result.multi_face_landmarks[0], intensity)
        face_app = self._get_face_app()
        original_faces = face_app.get(image)
        processed_faces = face_app.get(processed)
        if not original_faces or not processed_faces:
            raise ValueError("InsightFace could not detect a face in the image")

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
            "skin_tone": payload.get("skin_tone", "medium"),
            "undertone": payload.get("undertone", "warm"),
            "foundation_match": payload.get("foundation_match", "medium-warm"),
            "processed": True,
            "output_path": saved_path,
        }


class IdentityGuard:
    min_similarity = 0.85

    def validate(self, similarity: float, intensity: float) -> tuple[float, bool]:
        current_intensity = max(0.0, min(1.0, intensity))
        return current_intensity, float(similarity) >= self.min_similarity


class SkinToneMatcher:
    FitzpatrickMap = {
        1: {"tone": "very-light", "undertone": "cool"},
        2: {"tone": "light", "undertone": "cool"},
        3: {"tone": "medium", "undertone": "neutral"},
        4: {"tone": "olive", "undertone": "warm"},
        5: {"tone": "deep", "undertone": "warm"},
        6: {"tone": "very-deep", "undertone": "neutral"},
    }

    def detect(self, melanin_index: float) -> dict[str, str]:
        if melanin_index <= 0.75:
            fitzpatrick = 1
        elif melanin_index <= 1.3:
            fitzpatrick = 2
        elif melanin_index <= 2.1:
            fitzpatrick = 3
        elif melanin_index <= 3.0:
            fitzpatrick = 4
        elif melanin_index <= 4.3:
            fitzpatrick = 5
        else:
            fitzpatrick = 6
        return self.FitzpatrickMap[fitzpatrick]

    def recommend_foundation(self, skin_tone: str, undertone: str) -> str:
        return f"{skin_tone}-{undertone}"
