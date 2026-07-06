"""OCR バックグラウンドジョブ。

教材のページ画像を vision LLM で文字起こしする。asyncio のスレッドプールで
ページ単位に並列実行し、進捗を Job / Material に反映する。
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from sqlalchemy.orm import Session

from . import files, llm, prompts
from .config import settings
from .db import SessionLocal
from .models import Job, Material, MaterialPage


async def run_ocr_for_material(material_id: int, job_id: int) -> None:
    db = SessionLocal()
    try:
        material = db.get(Material, material_id)
        job = db.get(Job, job_id)
        if material is None or job is None:
            return
        pages = list(material.pages)
        job.total = len(pages)
        job.done = 0
        job.status = "running"
        material.status = "processing"
        db.commit()

        sem = asyncio.Semaphore(settings.ocr_concurrency)

        async def worker(page_id: int) -> None:
            async with sem:
                await asyncio.to_thread(_ocr_one_page, page_id)
                _bump_progress(job_id, material_id)

        await asyncio.gather(*(worker(p.id) for p in pages))

        db.refresh(material)
        db.refresh(job)
        any_error = any(p.status == "error" for p in material.pages)
        material.status = "error" if any_error else "ready"
        job.status = "error" if any_error else "done"
        job.progress = 1.0
        db.commit()
    except Exception as exc:  # noqa: BLE001
        _mark_failed(material_id, job_id, str(exc))
    finally:
        db.close()


def _ocr_one_page(page_id: int) -> None:
    db: Session = SessionLocal()
    try:
        page = db.get(MaterialPage, page_id)
        if page is None:
            return
        page.status = "processing"
        page.error = ""
        db.commit()
        try:
            image_bytes = files.load_image_bytes(Path(page.image_path))
            messages = prompts.ocr_messages(image_bytes)
            text = llm.chat(db, messages, vision=True, temperature=0.1)
            page.ocr_text = text.strip()
            page.status = "done"
        except Exception as exc:  # noqa: BLE001
            page.status = "error"
            page.error = str(exc)[:500]
        db.commit()
    finally:
        db.close()


def _bump_progress(job_id: int, material_id: int) -> None:
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if job is None:
            return
        job.done += 1
        job.progress = job.done / job.total if job.total else 1.0
        db.commit()
    finally:
        db.close()


def _mark_failed(material_id: int, job_id: int, error: str) -> None:
    db = SessionLocal()
    try:
        material = db.get(Material, material_id)
        job = db.get(Job, job_id)
        if material:
            material.status = "error"
            material.error = error[:500]
        if job:
            job.status = "error"
            job.error = error[:500]
        db.commit()
    finally:
        db.close()


def prepare_pages(db: Session, material: Material) -> int:
    """原本ファイルをページ画像に変換し MaterialPage を作成。ページ数を返す。"""
    page_paths = files.render_to_pages(
        Path(material.stored_path), material.id, material.original_filename
    )
    for i, p in enumerate(page_paths, start=1):
        db.add(
            MaterialPage(
                material_id=material.id,
                page_no=i,
                image_path=str(p),
                status="pending",
            )
        )
    db.commit()
    return len(page_paths)
