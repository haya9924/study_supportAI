"""生成用に教材の OCR テキストを収集する。"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Material, MaterialPage


def gather_context(
    db: Session, material_ids: list[int], course_id: int | None = None
) -> str:
    """指定教材(または科目全体)の OCR テキストを結合して返す。"""
    ids = list(material_ids)
    if not ids and course_id is not None:
        ids = [
            m.id
            for m in db.scalars(
                select(Material).where(Material.course_id == course_id)
            ).all()
        ]
    parts: list[str] = []
    for mid in ids:
        material = db.get(Material, mid)
        if material is None:
            continue
        texts = [p.ocr_text for p in material.pages if p.ocr_text.strip()]
        if texts:
            parts.append(f"## 教材: {material.title}\n" + "\n\n".join(texts))
    return "\n\n".join(parts)
