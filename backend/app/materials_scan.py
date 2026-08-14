"""教材ライブラリのフォルダスキャン (マウント方式)。

library/<科目>/<ファイル> を走査し、未登録のファイルを Material として登録する。
ページ画像の生成 (PDF ラスタライズ等) まではここで行うが、OCR は自動では行わず、
ユーザーが OCR ボタンを押したときに materials_router から開始する。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import ocr
from .config import settings
from .models import Course, Material
from .routers.plans_router import _ensure_plan_for_course

FILE_EXTS = {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff", ".heic", ".heif"}
META_SUFFIX = ".meta.json"

# 例: 2024_中間試験_生物.pdf → {year:"2024", exam_type:"中間試験"}
_FILENAME_PATTERN = re.compile(r"^(\d{4})_(.+)$")


def _ext_stripped(path: Path) -> str:
    return path.name.rsplit(".", 1)[0] if "." in path.name else path.name


def _parse_meta(path: Path) -> dict:
    """兄弟の <file>.meta.json を読む。無ければ空 dict。"""
    meta_path = path.with_name(path.name + META_SUFFIX)
    if meta_path.is_file():
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (OSError, json.JSONDecodeError):
            return {}
    return {}


def infer_metadata(filename: str) -> dict:
    """ファイル名とメタファイルから {kind, title, year, exam_type} を決める。

    - <file>.meta.json があれば {kind, year, exam_type} を優先
    - ファイル名が YYYY_試験名_... なら past_exam (year/試験名)
    - それ以外は lecture
    """
    meta: dict = {}
    try:
        path = Path(filename)
        meta = _parse_meta(path)
    except OSError:
        meta = {}

    stem = _ext_stripped(Path(filename))
    kind = str(meta.get("kind") or "lecture")
    year = str(meta.get("year") or "")
    exam_type = str(meta.get("exam_type") or "")
    title = str(meta.get("title") or "").strip()

    m = _FILENAME_PATTERN.match(stem)
    if m:
        if kind == "lecture" and not meta.get("year"):
            kind = "past_exam"
        year = year or m.group(1)
        exam_type = exam_type or m.group(2)

    if not title:
        title = stem
    return {"kind": kind, "title": title, "year": year, "exam_type": exam_type}


def _find_or_create_course(db: Session, name: str) -> Course:
    course = db.scalar(select(Course).where(Course.name == name))
    if course is None:
        course = Course(name=name)
        db.add(course)
        db.flush()
    return course


def library_root(db: Session) -> Path:
    """教材フォルダのルート。DB 設定 (設定画面で切替可) があればそれを使う。

    未設定の場合は環境変数 / 既定値 (library/) にフォールバックする。
    """
    from . import llm

    raw = llm.get_setting(db, "materials_dir").strip()
    path = Path(raw).expanduser() if raw else settings.materials_dir
    path = path.resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def scan_library(db: Session, *, create_jobs: bool = False) -> dict:
    """教材フォルダを走査し、未登録ファイルを Material として登録する。

    冪等: 登録済み (stored_path 一致) のファイルはスキップする。
    OCR ジョブは起動しない (create_jobs は常に False で保持)。
    戻り値: {"registered": [...], "skipped": n, "errors": [...]}
    """
    root = library_root(db)
    root.mkdir(parents=True, exist_ok=True)

    registered: list[dict] = []
    errors: list[str] = []

    def register(f: Path, course: Course | None):
        if not f.is_file():
            return
        ext = f.suffix.lower()
        if ext not in FILE_EXTS:
            return
        existing = db.scalar(select(Material).where(Material.stored_path == str(f)))
        if existing is not None:
            return

        meta = infer_metadata(f.name)
        material = Material(
            course_id=course.id if course else None,
            kind=meta["kind"],
            title=meta["title"],
            original_filename=f.name,
            stored_path=str(f),
            mime="application/octet-stream",
            year=meta["year"],
            exam_type=meta["exam_type"],
            status="uploaded",
        )
        db.add(material)
        db.commit()
        db.refresh(material)

        try:
            ocr.prepare_pages(db, material)
            # OCR は手動で開始する (uploaded のまま)
            material.status = "uploaded"
            db.commit()
        except Exception as exc:  # noqa: BLE001
            material.status = "error"
            material.error = str(exc)[:500]
            db.commit()
            errors.append(f"{f.name}: {exc}")

        registered.append(
            {
                "id": material.id,
                "name": material.title,
                "kind": material.kind,
                "course": course.name if course else None,
                "pages": len(material.pages),
            }
        )

    for course_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        course = _find_or_create_course(db, course_dir.name)
        _ensure_plan_for_course(db, course)
        for f in sorted(course_dir.iterdir()):
            register(f, course)

    # フォルダ直下のファイルは「未分類」として取り込む
    for f in sorted(root.iterdir()):
        register(f, None)

    db.commit()
    return {"registered": registered, "errors": errors}