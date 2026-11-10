"""Local, face-mesh-guided portrait effects.

These are deterministic 2-D cosmetic edits. They are deliberately not described
as generative age, gender, or identity transformations. The external generative
provider remains separately consent-gated for edits that need new pixels.
"""
from __future__ import annotations

from typing import Any

import cv2
import numpy as np


FACE_EDIT_OPTIONS = frozenset(
    {
        "none",
        "hair_black",
        "hair_brown",
        "hair_auburn",
        "hair_blonde",
        "soft_smile",
        "stubble",
        "short_beard",
        "full_beard",
        "mustache",
        "glasses_round",
        "glasses_square",
        "glasses_aviator",
        "slim_face",
        "v_shape",
        "age_mature",
        "youthful_finish",
        "masculine_presentation",
        "feminine_presentation",
    }
)


class FaceEffects:
    """Apply bounded local edits using MediaPipe Face Mesh landmarks."""

    _OUTER_LIPS = (
        61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291,
        308, 324, 318, 402, 317, 14, 87, 178, 88, 95, 78,
    )
    _JAW = (
        234, 93, 132, 58, 172, 136, 150, 149, 176, 148, 152,
        377, 400, 378, 379, 365, 397, 288, 361, 323, 454,
    )

    @classmethod
    def apply(
        cls,
        image: np.ndarray,
        landmarks: Any,
        edit: str = "none",
        intensity: float = 0.7,
    ) -> np.ndarray:
        """Return a new image with the requested local effect applied."""
        if edit not in FACE_EDIT_OPTIONS:
            raise ValueError("Unsupported face edit.")
        if image is None or image.ndim != 3 or image.size == 0:
            raise ValueError("A valid color portrait is required.")
        strength = float(np.clip(intensity, 0.0, 1.0))
        if edit == "none" or strength <= 0.0:
            return image.copy()

        points = cls._points(image, landmarks)
        if edit.startswith("hair_"):
            return cls._recolor_hair(image, points, edit, strength)
        if edit in {"glasses_round", "glasses_square", "glasses_aviator"}:
            return cls._glasses(image, points, edit, strength)
        if edit in {"stubble", "short_beard", "full_beard", "mustache"}:
            return cls._beard(image, points, edit, strength)
        if edit == "soft_smile":
            return cls._smile(image, points, strength)
        if edit in {"slim_face", "v_shape"}:
            return cls._reshape(image, points, edit, strength)
        if edit == "age_mature":
            return cls._mature_finish(image, points, strength)
        if edit == "youthful_finish":
            return cls._youthful_finish(image, points, strength)
        if edit == "masculine_presentation":
            styled = cls._beard(image, points, "stubble", strength)
            return cls._darken_brows(styled, points, strength)
        if edit == "feminine_presentation":
            return cls._feminine_finish(image, points, strength)
        return image.copy()

    @staticmethod
    def _points(image: np.ndarray, landmarks: Any) -> np.ndarray:
        raw = getattr(landmarks, "landmark", None)
        if raw is None or len(raw) < 468:
            raise ValueError("A complete face mesh is required for this edit.")
        height, width = image.shape[:2]
        points = np.asarray(
            [
                [
                    int(np.clip(round(float(point.x) * (width - 1)), 0, width - 1)),
                    int(np.clip(round(float(point.y) * (height - 1)), 0, height - 1)),
                ]
                for point in raw
            ],
            dtype=np.int32,
        )
        if not np.isfinite(points).all():
            raise ValueError("Face landmarks are invalid.")
        return points

    @staticmethod
    def _face_geometry(
        points: np.ndarray, image_shape: tuple[int, ...]
    ) -> tuple[int, int, int, int, int, int]:
        height, width = image_shape[:2]
        hull = cv2.convexHull(points)
        x, y, w, h = cv2.boundingRect(hull)
        if w < 24 or h < 24:
            raise ValueError("The detected face is too small for this edit.")
        return x, y, w, h, width, height

    @staticmethod
    def _blend_color(
        image: np.ndarray,
        mask: np.ndarray,
        color: tuple[int, int, int],
        opacity: float,
    ) -> np.ndarray:
        alpha = (mask.astype(np.float32) / 255.0 * float(np.clip(opacity, 0, 1)))[..., None]
        tint = np.asarray(color, dtype=np.float32).reshape(1, 1, 3)
        return np.clip(image.astype(np.float32) * (1.0 - alpha) + tint * alpha, 0, 255).astype(np.uint8)

    @classmethod
    def _recolor_hair(
        cls, image: np.ndarray, points: np.ndarray, edit: str, intensity: float
    ) -> np.ndarray:
        x, y, w, h, width, height = cls._face_geometry(points, image.shape)
        # MediaPipe does not provide hair segmentation. Restrict recoloring to
        # the head cap outside the face hull and reject likely skin pixels.
        center = (x + w // 2, max(0, y + int(h * 0.02)))
        axes = (max(8, int(w * 0.58)), max(8, int(h * 0.34)))
        head_mask = np.zeros((height, width), dtype=np.uint8)
        cv2.ellipse(head_mask, center, axes, 0, 0, 360, 255, -1)
        face_mask = np.zeros((height, width), dtype=np.uint8)
        cv2.fillConvexPoly(face_mask, cv2.convexHull(points), 255)
        candidate = cv2.bitwise_and(head_mask, cv2.bitwise_not(face_mask))

        ycrcb = cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)
        _, cr, cb = cv2.split(ycrcb)
        skin = ((cr >= 125) & (cr <= 195) & (cb >= 65) & (cb <= 145)).astype(np.uint8) * 255
        candidate = cv2.bitwise_and(candidate, cv2.bitwise_not(skin))
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        candidate = cv2.bitwise_and(candidate, (gray < 238).astype(np.uint8) * 255)
        candidate = cv2.GaussianBlur(candidate, (0, 0), sigmaX=max(1.0, w / 100.0))
        if int(np.count_nonzero(candidate)) < max(40, int(w * h * 0.015)):
            raise ValueError(
                "Hair is not clear enough to recolor. Use a front-facing photo with visible hair."
            )

        hue, saturation = {
            "hair_black": (0, 45),
            "hair_brown": (12, 125),
            "hair_auburn": (8, 175),
            "hair_blonde": (25, 150),
        }[edit]
        hls = cv2.cvtColor(image, cv2.COLOR_BGR2HLS).astype(np.float32)
        target = hls.copy()
        target[:, :, 0] = hue
        target[:, :, 2] = np.maximum(target[:, :, 2] * 0.45, saturation)
        if edit == "hair_black":
            target[:, :, 1] = np.clip(target[:, :, 1] * 0.52, 12, 95)
        elif edit == "hair_blonde":
            target[:, :, 1] = np.clip(target[:, :, 1] * 1.22 + 22, 70, 225)
        else:
            target[:, :, 1] = np.clip(target[:, :, 1] * 0.88 + 8, 25, 190)
        recolored = cv2.cvtColor(np.clip(target, 0, 255).astype(np.uint8), cv2.COLOR_HLS2BGR)
        alpha = (candidate.astype(np.float32) / 255.0 * 0.78 * intensity)[..., None]
        return np.clip(image.astype(np.float32) * (1 - alpha) + recolored.astype(np.float32) * alpha, 0, 255).astype(np.uint8)

    @classmethod
    def _glasses(
        cls, image: np.ndarray, points: np.ndarray, edit: str, intensity: float
    ) -> np.ndarray:
        height, width = image.shape[:2]
        required = (33, 133, 362, 263, 168, 127, 356)
        if len(points) <= max(required):
            raise ValueError("Eye landmarks are missing; choose a clearer portrait.")
        styled = image.copy()
        frame = {
            "glasses_round": (42, 35, 30),
            "glasses_square": (30, 28, 26),
            "glasses_aviator": (38, 142, 190),
        }[edit]
        thickness = max(1, int(round(width * 0.0055)))
        tint_mask = np.zeros((height, width), dtype=np.uint8)

        for outer, inner in ((33, 133), (362, 263)):
            p1, p2 = points[outer], points[inner]
            eye_width = max(8, int(np.linalg.norm(p2.astype(float) - p1.astype(float)) * 1.45))
            center = ((int(p1[0]) + int(p2[0])) // 2, (int(p1[1]) + int(p2[1])) // 2)
            eye_height = max(5, int(eye_width * (0.48 if edit == "glasses_square" else 0.58)))
            axes = (eye_width // 2, eye_height)
            cv2.ellipse(tint_mask, center, axes, 0, 0, 360, 255, -1)
            if edit == "glasses_square":
                left, top = center[0] - axes[0], center[1] - axes[1]
                right, bottom = center[0] + axes[0], center[1] + axes[1]
                cv2.rectangle(styled, (left, top), (right, bottom), frame, thickness, cv2.LINE_AA)
            else:
                cv2.ellipse(styled, center, axes, 0, 0, 360, frame, thickness, cv2.LINE_AA)

        # A subtle lens tint, nose bridge, and temple arms complete the frame.
        lens_alpha = tint_mask.astype(np.float32) / 255.0 * 0.08 * intensity
        lens_color = np.asarray((174, 190, 192), dtype=np.float32)
        styled = np.clip(styled.astype(np.float32) * (1 - lens_alpha[..., None]) + lens_color * lens_alpha[..., None], 0, 255).astype(np.uint8)
        left_inner = points[133]
        right_inner = points[362]
        bridge = points[168]
        cv2.line(styled, tuple(left_inner), tuple(bridge), frame, thickness, cv2.LINE_AA)
        cv2.line(styled, tuple(bridge), tuple(right_inner), frame, thickness, cv2.LINE_AA)
        cv2.line(styled, tuple(points[33]), tuple(points[127]), frame, thickness, cv2.LINE_AA)
        cv2.line(styled, tuple(points[263]), tuple(points[356]), frame, thickness, cv2.LINE_AA)
        return styled

    @classmethod
    def _beard(
        cls, image: np.ndarray, points: np.ndarray, edit: str, intensity: float
    ) -> np.ndarray:
        height, width = image.shape[:2]
        styled = image.copy()
        if edit == "mustache":
            left, right = points[61], points[291]
            center = ((int(left[0]) + int(right[0])) // 2, int((points[13][1] + points[14][1]) / 2))
            axes = (max(5, int(np.linalg.norm(right.astype(float) - left.astype(float)) * 0.55)), max(2, int(width * 0.012)))
            mask = np.zeros((height, width), dtype=np.uint8)
            cv2.ellipse(mask, center, axes, 0, 180, 360, 255, -1)
        else:
            jaw = points[list(cls._JAW)]
            mask = np.zeros((height, width), dtype=np.uint8)
            cv2.fillPoly(mask, [jaw], 255)
            # Keep the moustache/mouth and lip opening clean.
            if len(points) > max(cls._OUTER_LIPS):
                lip_mask = np.zeros_like(mask)
                cv2.fillPoly(lip_mask, [points[list(cls._OUTER_LIPS)]], 255)
                mask = cv2.bitwise_and(mask, cv2.bitwise_not(lip_mask))
            x, y, w, h = cv2.boundingRect(jaw)
            upper_limit = y + int(h * (0.43 if edit == "stubble" else 0.34))
            upper = np.zeros_like(mask)
            upper[upper_limit:, :] = 255
            mask = cv2.bitwise_and(mask, upper)

        mask = cv2.GaussianBlur(mask, (0, 0), sigmaX=max(0.8, width / 320.0))
        opacity = {"stubble": 0.30, "short_beard": 0.52, "full_beard": 0.68, "mustache": 0.66}[edit]
        styled = cls._blend_color(styled, mask, (32, 27, 25), opacity * intensity)

        # Fine deterministic stubble gives short beard presets some texture.
        if edit == "stubble":
            seed = np.random.default_rng(343)
            dots = np.zeros_like(mask)
            ys, xs = np.where(mask > 80)
            if len(xs):
                count = min(1800, max(80, len(xs) // 5))
                selection = seed.choice(len(xs), size=min(count, len(xs)), replace=False)
                for index in selection:
                    cv2.circle(dots, (int(xs[index]), int(ys[index])), 1, 255, -1)
                styled = cls._blend_color(styled, dots, (26, 23, 22), 0.45 * intensity)
        return styled

    @classmethod
    def _smile(cls, image: np.ndarray, points: np.ndarray, intensity: float) -> np.ndarray:
        height, width = image.shape[:2]
        face_width = max(1, int(points[454, 0] - points[234, 0]))
        face_height = max(1, int(points[152, 1] - points[10, 1]))
        lift = max(1.0, face_height * 0.028 * intensity)
        yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
        map_y = yy.copy()
        sigma_x = max(3.0, face_width * 0.075)
        sigma_y = max(3.0, face_height * 0.065)
        for corner_index in (61, 291):
            cx, cy = points[corner_index].astype(np.float32)
            weight = np.exp(-(((xx - cx) / sigma_x) ** 2 + ((yy - cy) / sigma_y) ** 2) * 0.5)
            map_y += lift * weight
        return cv2.remap(image, xx, map_y, interpolation=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT_101)

    @classmethod
    def _reshape(
        cls, image: np.ndarray, points: np.ndarray, edit: str, intensity: float
    ) -> np.ndarray:
        height, width = image.shape[:2]
        face_width = max(1, float(points[454, 0] - points[234, 0]))
        face_height = max(1, float(points[152, 1] - points[10, 1]))
        center_x = (float(points[234, 0]) + float(points[454, 0])) / 2.0
        center_y = float(points[10, 1]) + face_height * (0.67 if edit == "slim_face" else 0.75)
        yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
        vertical_scale = face_height * (0.27 if edit == "slim_face" else 0.22)
        horizontal_scale = face_width * 0.22
        weight = np.exp(-(((xx - center_x) / horizontal_scale) ** 2 + ((yy - center_y) / vertical_scale) ** 2) * 0.5)
        if edit == "v_shape":
            lower_gate = np.clip((yy - (points[10, 1] + face_height * 0.48)) / max(1.0, face_height * 0.22), 0, 1)
            weight *= lower_gate
        amount = 0.055 if edit == "slim_face" else 0.075
        map_x = xx + (xx - center_x) * amount * intensity * weight
        return cv2.remap(image, map_x, yy, interpolation=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT_101)

    @classmethod
    def _mature_finish(
        cls, image: np.ndarray, points: np.ndarray, intensity: float
    ) -> np.ndarray:
        height, width = image.shape[:2]
        styled = image.copy()
        face_width = max(1, int(points[454, 0] - points[234, 0]))
        face_height = max(1, int(points[152, 1] - points[10, 1]))
        color = (95, 92, 90)
        line_width = max(1, int(width * 0.002))
        y_values = (
            int(points[10, 1] + face_height * 0.30),
            int(points[10, 1] + face_height * 0.34),
            int(points[10, 1] + face_height * 0.38),
        )
        for index, y in enumerate(y_values):
            start = (int(points[234, 0] + face_width * 0.27), y)
            end = (int(points[454, 0] - face_width * 0.27), y + (index - 1) * 2)
            cv2.line(styled, start, end, color, line_width, cv2.LINE_AA)
        # Fine crow's-feet under the outer eye corners.
        for corner in (33, 263):
            cx, cy = points[corner]
            direction = -1 if corner == 33 else 1
            for offset in (-1, 0, 1):
                start = (int(cx), int(cy + offset * 2))
                end = (int(cx + direction * face_width * 0.055), int(cy + offset * 4 + face_height * 0.018))
                cv2.line(styled, start, end, color, line_width, cv2.LINE_AA)
        return cv2.addWeighted(image, 1.0 - 0.34 * intensity, styled, 0.34 * intensity, 0)

    @classmethod
    def _youthful_finish(
        cls, image: np.ndarray, points: np.ndarray, intensity: float
    ) -> np.ndarray:
        height, width = image.shape[:2]
        face_mask = np.zeros((height, width), dtype=np.uint8)
        cv2.fillConvexPoly(face_mask, cv2.convexHull(points), 255)
        face_mask = cv2.GaussianBlur(face_mask, (0, 0), sigmaX=max(1.0, width / 100.0))
        smooth = cv2.bilateralFilter(image, d=0, sigmaColor=28, sigmaSpace=18)
        alpha = (face_mask.astype(np.float32) / 255.0 * 0.30 * intensity)[..., None]
        return np.clip(image.astype(np.float32) * (1 - alpha) + smooth.astype(np.float32) * alpha, 0, 255).astype(np.uint8)

    @classmethod
    def _darken_brows(
        cls, image: np.ndarray, points: np.ndarray, intensity: float
    ) -> np.ndarray:
        styled = image.copy()
        for contour in (
            (70, 63, 105, 66, 107, 55),
            (300, 293, 334, 296, 336, 285),
        ):
            if len(points) <= max(contour):
                continue
            path = points[list(contour)]
            cv2.polylines(
                styled, [path], False, (35, 28, 24),
                max(1, int(round(image.shape[1] * 0.006))),
                cv2.LINE_AA,
            )
        return cv2.addWeighted(image, 1.0 - 0.55 * intensity, styled, 0.55 * intensity, 0)

    @classmethod
    def _feminine_finish(
        cls, image: np.ndarray, points: np.ndarray, intensity: float
    ) -> np.ndarray:
        height, width = image.shape[:2]
        styled = image.astype(np.float32)
        cheek_mask = np.zeros((height, width), dtype=np.uint8)
        x, y, w, h, _, _ = cls._face_geometry(points, image.shape)
        axes = (max(3, int(w * 0.095)), max(2, int(h * 0.032)))
        cy = y + int(h * 0.63)
        cv2.ellipse(cheek_mask, (x + int(w * 0.32), cy), axes, -8, 0, 360, 255, -1)
        cv2.ellipse(cheek_mask, (x + int(w * 0.68), cy), axes, 8, 0, 360, 255, -1)
        face_mask = np.zeros((height, width), dtype=np.uint8)
        cv2.fillConvexPoly(face_mask, cv2.convexHull(points), 255)
        cheek_mask = cv2.bitwise_and(cheek_mask, face_mask)
        cheek_mask = cv2.GaussianBlur(cheek_mask, (0, 0), sigmaX=max(1.0, width / 55.0))
        cheek_alpha = (cheek_mask.astype(np.float32) / 255.0 * 0.11 * intensity)[..., None]
        blush = np.asarray((142, 92, 210), dtype=np.float32).reshape(1, 1, 3)
        styled = styled * (1 - cheek_alpha) + blush * cheek_alpha

        lip_mask = np.zeros((height, width), dtype=np.uint8)
        cv2.fillPoly(lip_mask, [points[list(cls._OUTER_LIPS)]], 255)
        lip_mask = cv2.GaussianBlur(lip_mask, (0, 0), sigmaX=max(0.8, width / 420.0))
        lip_alpha = (lip_mask.astype(np.float32) / 255.0 * 0.22 * intensity)[..., None]
        lipstick = np.asarray((104, 55, 185), dtype=np.float32).reshape(1, 1, 3)
        styled = styled * (1 - lip_alpha) + lipstick * lip_alpha
        return np.clip(styled, 0, 255).astype(np.uint8)
