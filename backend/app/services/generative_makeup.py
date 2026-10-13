"""Optional generative makeup and hairstyle edits via the OpenAI Images API.

Source photos are sent to the configured provider only when the caller has
explicitly confirmed third-party processing consent. Provider keys remain server-side.
"""
import base64
import binascii
import logging
import mimetypes
import uuid
from io import BytesIO
from pathlib import Path
from typing import Any

import httpx
from PIL import Image, UnidentifiedImageError

from app.core.config import settings

logger = logging.getLogger("makeupart.generative_makeup")

_LOOK_PROMPTS = {
    "natural": "natural everyday makeup: subtle foundation matched to the exact existing skin tone, light blush, softly defined lashes and a natural lip tint",
    "soft_glam": "polished soft-glam makeup: softly blended neutral eyeshadow, delicate eyeliner, defined lashes, subtle cheek blush and contour, satin lipstick",
    "full_glam": "full professional glam makeup: expertly blended eyeshadow, clean eyeliner, defined lashes, refined contour and blush, realistic skin texture and a rich balanced lipstick",
    "bridal_glam": "timeless bridal makeup: realistic luminous skin, softly blended rose/champagne eyeshadow, elegant eyeliner, natural defined lashes, rose blush and rose-nude lipstick",
    "smokey_eye": "professionally blended smokey-eye makeup with a smooth charcoal-brown gradient, soft eyeliner, defined lashes, subtle blush and neutral lips",
    "cat_eye": "elegant cat-eye eyeliner with a precise lifted outer wing, restrained neutral eyeshadow, defined lashes, subtle blush and a flattering lip color",
    "eyeshadow": "professionally blended eyeshadow with a wearable gradient, smooth transitions, realistic texture and a complementary color palette",
    "eyeliner": "precise salon-quality eyeliner following the natural eyelid shape, a refined line and tasteful outer wing, without altering eye shape or eyelid anatomy",
    "lipstick": "professional lipstick application with clean lip edges, even color coverage, natural lip texture and a complementary lip color",
    "blush": "subtle professionally placed cheek blush blended into the existing skin, preserving real skin texture and the exact original complexion",
    "foundation": "realistic foundation matched to the person's exact original skin tone and undertone, natural skin texture, even coverage, no skin lightening and no plastic skin",
    "editorial": "high-fashion beauty editorial makeup: refined artistic eyeshadow, precise eyeliner, polished blush and a bold complementary lip, photorealistic",
    "sleek_hair": "a polished salon sleek hairstyle that respects the person's original hairline, natural color, texture and approximate length",
    "soft_curls": "soft defined salon curls with realistic strand texture, preserving the original hairline, natural hair color and approximate length",
    "braided_style": "a neat salon braided hairstyle suited to the existing hair length and texture, preserving the hairline, natural color and cultural hair texture",
    "elegant_updo": "an elegant salon updo appropriate for a formal event, respecting the existing hairline, natural hair texture and color while keeping facial features unchanged",
}


class GenerativeMakeupProvider:
    """Run a controlled image edit and store its PNG inside salon media."""

    endpoint = "https://api.openai.com/v1/images/edits"
    allowed_looks = frozenset(_LOOK_PROMPTS)
    max_output_bytes = 25 * 1024 * 1024

    @classmethod
    def is_ready(cls) -> bool:
        return bool(settings.OPENAI_API_KEY.strip())

    @staticmethod
    def _prompt(look: str, intensity: float) -> str:
        if look not in _LOOK_PROMPTS:
            raise ValueError("Unsupported generative look.")
        strength = max(0.0, min(1.0, float(intensity)))
        if strength < 0.26:
            amount = "very subtle; barely noticeable cosmetic changes"
        elif strength < 0.66:
            amount = "moderate; visible but tasteful and realistic"
        else:
            amount = "expressive and clearly visible while remaining professionally tasteful"
        return (
            "Edit the supplied real client portrait for a professional beauty salon. Apply "
            f"only this requested treatment: {_LOOK_PROMPTS[look]}. Treatment strength: {amount}. "
            "Preservation requirements: keep the same person and preserve face shape, facial "
            "proportions, eye spacing, nose, lips, skin tone, undertone, age appearance, expression, "
            "gaze, pose, clothing, background, camera angle and lighting as closely as possible. "
            "Do not change facial anatomy, do not lighten or darken complexion, do not remove "
            "natural features, and do not make skin look plastic. Change only cosmetic pigment "
            "or hairstyle details needed for the selected treatment. Keep the result photorealistic "
            "and salon-ready. Return one edited image only, with no collage, comparison labels, "
            "text, or watermark."
        )

    def process(self, image_path: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
        options = options or {}
        api_key = settings.OPENAI_API_KEY.strip()
        if not api_key:
            raise RuntimeError(
                "Generative makeup is not configured. The administrator must set OPENAI_API_KEY."
            )

        source = Path(image_path).resolve()
        if not source.is_file():
            raise FileNotFoundError("Input image not found.")
        look = str(options.get("generative_look", "full_glam"))
        intensity = float(options.get("intensity", 0.7))
        prompt = self._prompt(look, intensity)
        configured_output = str(options.get("output_dir", "")).strip()
        if not configured_output:
            raise ValueError("A salon-scoped output directory is required.")
        output_dir = Path(configured_output).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        mime_type = mimetypes.guess_type(source.name)[0] or "image/png"
        if mime_type not in {"image/jpeg", "image/png", "image/webp"}:
            mime_type = "image/png"
        form = {
            "model": settings.OPENAI_IMAGE_MODEL,
            "prompt": prompt,
            "quality": settings.OPENAI_IMAGE_QUALITY,
            "size": "auto",
            "output_format": "png",
            "moderation": "auto",
        }

        try:
            with source.open("rb") as image_stream:
                response = httpx.post(
                    self.endpoint,
                    headers={"Authorization": f"Bearer {api_key}"},
                    data=form,
                    files={"image[]": (source.name, image_stream, mime_type)},
                    timeout=httpx.Timeout(180.0, connect=20.0),
                )
        except httpx.TimeoutException as exc:
            logger.warning("Generative makeup provider timed out.")
            raise RuntimeError("Generative makeup timed out. Try again with a clear, well-lit photo.") from exc
        except httpx.HTTPError as exc:
            logger.warning("Generative makeup provider connection failed (%s).", type(exc).__name__)
            raise RuntimeError("Generative makeup service could not be reached. Try again later.") from exc

        if response.status_code in (401, 403):
            logger.error("Generative provider rejected configured credentials (HTTP %s).", response.status_code)
            raise RuntimeError("Generative makeup provider credentials are not accepted.")
        if response.status_code == 429:
            logger.warning("Generative makeup provider rate or usage limit reached.")
            raise RuntimeError("Generative AI usage limit reached. Try again later.")
        if response.status_code >= 500:
            logger.warning("Generative makeup provider returned HTTP %s.", response.status_code)
            raise RuntimeError("Generative makeup is temporarily unavailable. Try again later.")
        if not 200 <= response.status_code < 300:
            logger.warning("Generative makeup request rejected (HTTP %s).", response.status_code)
            raise RuntimeError(
                f"Generative makeup request was rejected (HTTP {response.status_code}). "
                "Check model access and provider configuration."
            )

        try:
            payload = response.json()
            encoded = payload["data"][0]["b64_json"]
            image_bytes = base64.b64decode(encoded, validate=True)
        except (ValueError, TypeError, KeyError, IndexError, binascii.Error) as exc:
            logger.error("Generative provider returned an invalid image payload.")
            raise RuntimeError("Generative makeup provider returned an invalid image.") from exc

        if not image_bytes or len(image_bytes) > self.max_output_bytes:
            raise RuntimeError("Generative output is empty or too large to process safely.")

        try:
            with Image.open(BytesIO(image_bytes)) as check:
                width, height = check.size
                if width <= 0 or height <= 0 or width * height > settings.MAX_IMAGE_PIXELS:
                    raise RuntimeError("Generative output dimensions exceed the safe image limit.")
                check.verify()
            with Image.open(BytesIO(image_bytes)) as image:
                normalized = image.convert("RGB")
                output_path = output_dir / f"generative_{uuid.uuid4().hex}.png"
                temp_path = output_dir / f".{output_path.name}.tmp"
                try:
                    normalized.save(temp_path, format="PNG", optimize=True)
                    temp_path.replace(output_path)
                finally:
                    temp_path.unlink(missing_ok=True)
        except RuntimeError:
            raise
        except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
            logger.error("Generative provider returned invalid image bytes.")
            raise RuntimeError("Generative makeup provider returned an invalid image.") from exc

        return {
            "processed": True,
            "engine": "generative",
            "generative_look": look,
            "output_path": str(output_path.resolve()),
        }
