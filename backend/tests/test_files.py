"""PDF / 画像 → ページ画像変換テスト。サンプルは動的生成する。"""
import io
from pathlib import Path

import pypdfium2 as pdfium  # noqa: F401  (依存確認)
from PIL import Image

from app import files


def _make_pdf(path: Path, pages: int = 2):
    # Pillow で複数ページ PDF を生成
    imgs = [Image.new("RGB", (200, 280), "white") for _ in range(pages)]
    imgs[0].save(path, save_all=True, append_images=imgs[1:], format="PDF")


def _make_jpeg(path: Path):
    Image.new("RGB", (3000, 2000), "white").save(path, format="JPEG")


def test_render_pdf(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    _make_pdf(pdf_path, pages=3)
    pages = files.render_to_pages(pdf_path, material_id=9001, filename="sample.pdf")
    assert len(pages) == 3
    assert all(p.exists() and p.suffix == ".jpg" for p in pages)


def test_render_jpeg_downscales(tmp_path):
    jpg_path = tmp_path / "big.jpg"
    _make_jpeg(jpg_path)
    pages = files.render_to_pages(jpg_path, material_id=9002, filename="big.jpg")
    assert len(pages) == 1
    with Image.open(pages[0]) as img:
        # 長辺が image_max_edge 以下に縮小される
        assert max(img.size) <= 1600


def test_unsupported_ext(tmp_path):
    bad = tmp_path / "note.txt"
    bad.write_text("hello")
    try:
        files.render_to_pages(bad, material_id=9003, filename="note.txt")
        assert False, "例外が発生するはず"
    except ValueError:
        pass
