import io

from PIL import Image

from scraper.photos import downscale_and_save


def _make_jpeg(size=(800, 1000)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color=(128, 64, 200)).save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def test_downscale_reduces_size_and_dimensions(tmp_path):
    raw = _make_jpeg()
    dest = tmp_path / "photo.jpg"

    assert downscale_and_save(raw, dest) is True

    with Image.open(dest) as im:
        assert im.size[0] <= 250
        assert im.size[1] <= 312
        assert im.format == "JPEG"

    assert dest.stat().st_size < len(raw)


def test_downscale_rejects_non_image(tmp_path):
    dest = tmp_path / "nope.jpg"
    assert downscale_and_save(b"not an image", dest) is False
    assert not dest.exists()
