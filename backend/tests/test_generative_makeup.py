import base64
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from app.core.config import settings
from app.services.generative_makeup import GenerativeMakeupProvider


def _png_bytes(color=(80, 90, 100), size=(32, 32)):
    output = BytesIO()
    Image.new("RGB", size, color).save(output, format="PNG")
    return output.getvalue()


class _FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def test_generative_provider_is_disabled_without_server_key(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    source = tmp_path / "source.png"
    source.write_bytes(_png_bytes())
    provider = GenerativeMakeupProvider()
    assert provider.is_ready() is False
    with pytest.raises(RuntimeError, match="not configured"):
        provider.process(str(source), {"output_dir": str(tmp_path / "output")})


def test_generative_provider_edits_image_and_stores_png_inside_output_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "server-side-test-key")
    monkeypatch.setattr(settings, "OPENAI_IMAGE_MODEL", "gpt-image-2.5-sunburst")
    monkeypatch.setattr(settings, "OPENAI_IMAGE_QUALITY", "medium")
    source = tmp_path / "source.png"
    source.write_bytes(_png_bytes())
    output_dir = tmp_path / "salons" / "salon-a" / "outputs"
    captured = {}

    def fake_post(url, *, headers, data, files, timeout):
        captured.update(url=url, headers=headers, data=data, filename=files["image[]"][0],
                        content_type=files["image[]"][2], input_bytes=files["image[]"][1].read())
        return _FakeResponse(200, {"data": [{
            "b64_json": base64.b64encode(_png_bytes((10, 180, 90))).decode()
        }]})

    monkeypatch.setattr("app.services.generative_makeup.httpx.post", fake_post)
    result = GenerativeMakeupProvider().process(
        str(source),
        {"output_dir": str(output_dir), "generative_look": "smokey_eye", "intensity": 0.82},
    )

    saved = Path(result["output_path"])
    assert result["processed"] is True
    assert result["generative_look"] == "smokey_eye"
    assert saved.parent == output_dir.resolve()
    assert saved.suffix == ".png"
    with Image.open(saved) as image:
        assert image.size == (32, 32)
        assert image.getpixel((0, 0)) == (10, 180, 90)
    assert captured["url"] == GenerativeMakeupProvider.endpoint
    assert captured["headers"]["Authorization"] == "Bearer server-side-test-key"
    assert captured["data"]["model"] == "gpt-image-2.5-sunburst"
    assert captured["data"]["output_format"] == "png"
    assert "same person" in captured["data"]["prompt"]
    assert "smokey-eye" in captured["data"]["prompt"]
    assert captured["input_bytes"] == source.read_bytes()


@pytest.mark.parametrize("look", ["unknown", "", None])
def test_generative_provider_rejects_unknown_look(look):
    with pytest.raises(ValueError, match="Unsupported generative look"):
        GenerativeMakeupProvider._prompt(look, 0.7)


def test_generative_provider_rejects_bad_provider_image(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "server-side-test-key")
    source = tmp_path / "source.png"
    source.write_bytes(_png_bytes())
    monkeypatch.setattr(
        "app.services.generative_makeup.httpx.post",
        lambda *args, **kwargs: _FakeResponse(200, {"data": [{"b64_json": "!!!"}]}),
    )
    with pytest.raises(RuntimeError, match="invalid image"):
        GenerativeMakeupProvider().process(str(source), {"output_dir": str(tmp_path / "output")})
