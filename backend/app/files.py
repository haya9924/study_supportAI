"""アップロードファイル → ページ画像 (JPEG) 変換。

- PDF: pypdfium2 で各ページを DPI 指定でラスタライズ。
- HEIC/HEIF: pillow-heif で読み込み。
- 画像 (JPEG/PNG/HEIC): 長辺を image_max_edge に縮小して JPEG 保存。
"""
from __future__ import annotations

import io
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image
import pillow_heif

from .config import settings

pillow_heif.register_heif_opener()


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
HEIC_EXTS = {".heic", ".heif"}


def _save_jpeg(img: Image.Image, out_path: Path) -> None:
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    max_edge = settings.image_max_edge
    w, h = img.size
    if max(w, h) > max_edge:
        scale = max_edge / max(w, h)
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="JPEG", quality=85)


def render_to_pages(
    stored_path: Path, material_id: int, filename: str
) -> list[Path]:
    """原本ファイルをページ画像 JPEG のリストに変換し、そのパスを返す。"""
    out_dir = settings.pages_dir / str(material_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(filename).suffix.lower()
    pages: list[Path] = []

    if ext == ".pdf":
        pdf = pdfium.PdfDocument(str(stored_path))
        try:
            n = min(len(pdf), settings.max_pages_per_material)
            scale = settings.pdf_render_dpi / 72.0
            for i in range(n):
                page = pdf[i]
                bitmap = page.render(scale=scale)
                pil = bitmap.to_pil()
                out_path = out_dir / f"page_{i + 1:04d}.jpg"
                _save_jpeg(pil, out_path)
                pages.append(out_path)
        finally:
            pdf.close()
        return pages

    # 単一画像 (HEIC 含む: opener 登録済み)
    if ext in IMAGE_EXTS or ext in HEIC_EXTS:
        with Image.open(stored_path) as img:
            img.load()
            out_path = out_dir / "page_0001.jpg"
            _save_jpeg(img, out_path)
            pages.append(out_path)
        return pages

    raise ValueError(f"未対応のファイル形式です: {ext}")


def load_image_bytes(image_path: Path) -> bytes:
    return Path(image_path).read_bytes()
