#!/usr/bin/env python3
"""Apply MOOG 343's public website favicon to Android launcher icon sizes.

Chrome's chrome://favicon2 URL is an internal browser URL, not a shareable image
resource. Fetch the favicon from the blog's public URL/Google favicon service.
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[2]
ANDROID_RES = ROOT / "makeup_art_v8" / "android" / "app" / "src" / "main" / "res"
SOURCES = (
    "https://www.google.com/s2/favicons?domain=moog-digital.blogspot.com&sz=256",
    "https://moog-digital.blogspot.com/favicon.ico",
    "https://www.google.com/s2/favicons?domain_url=https%3A%2F%2Fmoog-digital.blogspot.com%2F&sz=256",
)
DENSITIES = {
    "mipmap-mdpi": 48,
    "mipmap-hdpi": 72,
    "mipmap-xhdpi": 96,
    "mipmap-xxhdpi": 144,
    "mipmap-xxxhdpi": 192,
}


def fetch_icon() -> tuple[Image.Image, str]:
    errors: list[str] = []
    for url in SOURCES:
        try:
            request = Request(url, headers={"User-Agent": "MOOG-343-Android-Branding/1.0"})
            with urlopen(request, timeout=20) as response:
                payload = response.read(2_000_001)
            if not payload or len(payload) > 2_000_000:
                raise ValueError("empty icon or response larger than 2 MB")
            with Image.open(BytesIO(payload)) as image:
                image.load()
                if image.width < 8 or image.height < 8:
                    raise ValueError(f"icon too small: {image.width}x{image.height}")
                return image.convert("RGBA"), url
        except (URLError, OSError, ValueError) as error:
            errors.append(f"{url}: {error}")
    raise SystemExit("Unable to retrieve the MOOG 343 website favicon:\\n" + "\\n".join(errors))


def main() -> None:
    image, source_url = fetch_icon()
    print(f"Using MOOG 343 site favicon from {source_url} ({image.width}x{image.height})")
    for density, size in DENSITIES.items():
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        icon = ImageOps.contain(image, (size, size), method=Image.Resampling.LANCZOS)
        canvas.alpha_composite(icon, ((size - icon.width) // 2, (size - icon.height) // 2))
        target = ANDROID_RES / density / "ic_launcher.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(target, format="PNG", optimize=True)
        print(f"Wrote {target.relative_to(ROOT)} ({size}x{size})")


if __name__ == "__main__":
    main()
