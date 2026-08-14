"""生成用に教材の OCR テキストを収集する。"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Material


def _resolve_ids(
    db: Session, material_ids: list[int], course_id: int | None
) -> list[int]:
    ids = list(material_ids)
    if not ids and course_id is not None:
        ids = [
            m.id
            for m in db.scalars(
                select(Material).where(Material.course_id == course_id)
            ).all()
        ]
    return ids


def _material_text(material: Material) -> str:
    texts = [p.ocr_text for p in material.pages if p.ocr_text.strip()]
    return "\n\n".join(texts)


def gather_context(
    db: Session, material_ids: list[int], course_id: int | None = None
) -> str:
    """指定教材(または科目全体)の OCR テキストを結合して返す。

    テスト情報(kind=test_info)はテストの形式メモなので、フラッシュカードや
    クイズの学習素材には混ざらないよう除外する。
    """
    parts: list[str] = []
    for mid in _resolve_ids(db, material_ids, course_id):
        material = db.get(Material, mid)
        if material is None or material.kind == "test_info":
            continue
        text = _material_text(material)
        if text:
            parts.append(f"## 教材: {material.title}\n" + text)
    return "\n\n".join(parts)
