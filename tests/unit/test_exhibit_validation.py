"""Security tests for frozen visual claim decoding."""

import base64
import json
from pathlib import Path
from typing import Self

import pytest

from eros.app import research_lab

ROOT = Path(__file__).parents[2]


def test_frozen_claim_images_are_bounded_jpegs() -> None:
    registry = json.loads(
        (ROOT / "assets" / "crashmeter_v3" / "backtests_b64.json").read_text(
            encoding="utf-8"
        )
    )

    for exhibit in registry:
        _header, encoded = exhibit["src"].split(",", maxsplit=1)
        image_bytes, width, height = research_lab._validated_jpeg(encoded)
        assert image_bytes.startswith(b"\xff\xd8\xff")
        assert 0 < width * height <= 20_000_000


def test_oversized_claim_dimensions_are_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    class OversizedImage:
        format = "JPEG"
        size = (5000, 5000)

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def verify(self) -> None:
            return None

    monkeypatch.setattr(research_lab.Image, "open", lambda _stream: OversizedImage())
    encoded = base64.b64encode(b"\xff\xd8\xffbounded-test\xff\xd9").decode("ascii")

    with pytest.raises(ValueError, match="20 megapixel"):
        research_lab._validated_jpeg(encoded)


def test_oversized_base64_is_rejected_before_decode(monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected_decode(*_args: object, **_kwargs: object) -> bytes:
        raise AssertionError("decoder must not be called")

    monkeypatch.setattr(research_lab.base64, "b64decode", unexpected_decode)
    oversized = "A" * (research_lab.MAX_EXHIBIT_BASE64_LENGTH + 1)

    with pytest.raises(ValueError, match="encoded-size"):
        research_lab._validated_jpeg(oversized)


def test_pillow_bomb_error_is_normalized_to_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def bomb(_stream: object) -> object:
        raise research_lab.Image.DecompressionBombError("bomb")

    monkeypatch.setattr(research_lab.Image, "open", bomb)
    encoded = base64.b64encode(b"\xff\xd8\xffbounded-test\xff\xd9").decode("ascii")

    with pytest.raises(ValueError, match="invalid JPEG"):
        research_lab._validated_jpeg(encoded)


def test_research_source_never_renders_absolute_runtime_path() -> None:
    source = (ROOT / "src" / "eros" / "app" / "research_lab.py").read_text(
        encoding="utf-8"
    )
    assert "legacy_path.as_posix()" not in source
    assert "Provenance:" not in source


@pytest.mark.parametrize(
    "encoded",
    (
        "not-valid-base64!",
        base64.b64encode(b"not-a-jpeg").decode("ascii"),
        base64.b64encode(b"\xff\xd8\xfftrailing-without-eoi").decode("ascii"),
    ),
)
def test_malformed_or_unbounded_claim_images_are_rejected(encoded: str) -> None:
    with pytest.raises((ValueError, research_lab.binascii.Error)):
        research_lab._validated_jpeg(encoded)
