"""教材アップロード / OCR API。"""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import materials_scan, ocr, schemas
from ..config import settings
from ..db import get_db
from ..models import Course, Job, Material, MaterialPage

router = APIRouter(prefix="/api/materials", tags=["materials"])


@router.get("", response_model=list[schemas.MaterialOut])
def list_materials(
    course_id: int | None = None,
    uncategorized: bool = False,
    kind: str | None = None,
    db: Session = Depends(get_db),
):
    # マウントされたフォルダを自動スキャンして新規教材を取り込む (冪等・OCRは起動しない)
    try:
        materials_scan.scan_library(db)
    except Exception:  # noqa: BLE001
        pass
    stmt = select(Material).order_by(Material.created_at.desc())
    if uncategorized:
        stmt = stmt.where(Material.course_id.is_(None))
    elif course_id is not None:
        stmt = stmt.where(Material.course_id == course_id)
    if kind:
        stmt = stmt.where(Material.kind == kind)
    return db.scalars(stmt).all()


@router.post("/scan")
def scan_materials(db: Session = Depends(get_db)):
    """教材フォルダを再スキャンして未登録ファイルを取り込む。"""
    return materials_scan.scan_library(db)


@router.get("/{material_id}", response_model=schemas.MaterialDetail)
def get_material(material_id: int, db: Session = Depends(get_db)):
    material = db.get(Material, material_id)
    if material is None:
        raise HTTPException(404, "教材が見つかりません")
    return material


@router.post("/text", response_model=schemas.MaterialOut)
def create_text_material(
    payload: schemas.MaterialTextIn, db: Session = Depends(get_db)
):
    """テキストのみの教材(テスト情報など)を作成する。OCR は不要で即 ready。"""
    text = payload.text.strip()
    if not text:
        raise HTTPException(400, "テキストを入力してください")
    material = Material(
        course_id=payload.course_id,
        kind=payload.kind or "test_info",
        title=payload.title.strip() or "テスト情報",
        original_filename="",
        stored_path="",
        mime="text/plain",
        status="ready",
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    db.add(
        MaterialPage(
            material_id=material.id,
            page_no=1,
            image_path="",
            ocr_text=text,
            status="done",
        )
    )
    db.commit()
    db.refresh(material)
    return material


@router.post("", response_model=list[schemas.MaterialOut])
async def upload_materials(
    files: list[UploadFile] = File(...),
    course_id: int | None = Form(None),
    kind: str = Form("lecture"),
    db: Session = Depends(get_db),
):
    """ブラウザからのアップロード (互換用)。OCR は自動では起動せず手動で開始する。"""
    created: list[Material] = []
    for uf in files:
        suffix = Path(uf.filename or "file").suffix
        stored_name = f"{uuid.uuid4().hex}{suffix}"
        stored_path = settings.uploads_dir / stored_name
        with stored_path.open("wb") as out:
            shutil.copyfileobj(uf.file, out)
        material = Material(
            course_id=course_id,
            kind=kind,
            title=(uf.filename or "教材"),
            original_filename=uf.filename or stored_name,
            stored_path=str(stored_path),
            mime=uf.content_type or "",
            status="uploaded",
        )
        db.add(material)
        db.commit()
        db.refresh(material)

        # ページ画像生成 (同期・軽量)。OCR は手動で開始する。
        try:
            n = ocr.prepare_pages(db, material)
        except Exception as exc:  # noqa: BLE001
            material.status = "error"
            material.error = str(exc)[:500]
            db.commit()
            created.append(material)
            continue

        created.append(material)

    return created


@router.post("/{material_id}/ocr")
def start_ocr(
    material_id: int, background: BackgroundTasks, db: Session = Depends(get_db)
):
    """OCR を手動で開始する。未実施ページを文字起こしする。"""
    material = db.get(Material, material_id)
    if material is None:
        raise HTTPException(404, "教材が見つかりません")
    if material.status == "processing":
        raise HTTPException(409, "すでに OCR を実行中です")
    if not material.pages:
        raise HTTPException(400, "ページがありません")
    job = Job(type="ocr", target_id=material.id, status="running", total=len(material.pages))
    db.add(job)
    material.status = "processing"
    material.error = ""
    db.commit()
    db.refresh(job)
    background.add_task(ocr.run_ocr_for_material, material.id, job.id)
    return {"ok": True, "material_id": material.id, "job_id": job.id}


@router.put("/{material_id}/meta", response_model=schemas.MaterialOut)
def update_meta(
    material_id: int, payload: schemas.MaterialMetaIn, db: Session = Depends(get_db)
):
    """種別・タイトル・年度・試験名を手動で編集する。"""
    material = db.get(Material, material_id)
    if material is None:
        raise HTTPException(404, "教材が見つかりません")
    material.kind = payload.kind or material.kind
    if payload.title is not None:
        material.title = payload.title.strip() or material.title
    material.year = payload.year
    material.exam_type = payload.exam_type
    db.commit()
    db.refresh(material)
    return material


@router.get("/{material_id}/pages/{page_no}/image")
def get_page_image(material_id: int, page_no: int, db: Session = Depends(get_db)):
    page = db.scalar(
        select(MaterialPage).where(
            MaterialPage.material_id == material_id, MaterialPage.page_no == page_no
        )
    )
    if page is None or not page.image_path:
        raise HTTPException(404, "ページ画像が見つかりません")
    return FileResponse(page.image_path, media_type="image/jpeg")


@router.put("/pages/{page_id}", response_model=schemas.PageOut)
def update_page_text(
    page_id: int, payload: schemas.PageTextIn, db: Session = Depends(get_db)
):
    page = db.get(MaterialPage, page_id)
    if page is None:
        raise HTTPException(404, "ページが見つかりません")
    page.ocr_text = payload.ocr_text
    page.status = "done"
    db.commit()
    db.refresh(page)
    return page


@router.post("/pages/{page_id}/reocr", response_model=schemas.PageOut)
def reocr_page(
    page_id: int, background: BackgroundTasks, db: Session = Depends(get_db)
):
    page = db.get(MaterialPage, page_id)
    if page is None:
        raise HTTPException(404, "ページが見つかりません")
    page.status = "pending"
    db.commit()
    background.add_task(ocr._ocr_one_page, page.id)
    db.refresh(page)
    return page


@router.get("/{material_id}/status")
def material_status(material_id: int, db: Session = Depends(get_db)):
    material = db.get(Material, material_id)
    if material is None:
        raise HTTPException(404, "教材が見つかりません")
    job = db.scalar(
        select(Job)
        .where(Job.type == "ocr", Job.target_id == material_id)
        .order_by(Job.created_at.desc())
    )
    return {
        "material_status": material.status,
        "progress": job.progress if job else 0.0,
        "done": job.done if job else 0,
        "total": job.total if job else 0,
        "pages": [
            {"id": p.id, "page_no": p.page_no, "status": p.status}
            for p in material.pages
        ],
    }


@router.put("/{material_id}/move", response_model=schemas.MaterialOut)
def move_material(
    material_id: int, payload: schemas.MaterialMoveIn, db: Session = Depends(get_db)
):
    material = db.get(Material, material_id)
    if material is None:
        raise HTTPException(404, "教材が見つかりません")
    if payload.course_id is not None and db.get(Course, payload.course_id) is None:
        raise HTTPException(404, "移動先の科目が見つかりません")
    material.course_id = payload.course_id
    db.commit()
    db.refresh(material)
    return material


@router.delete("/{material_id}")
def delete_material(material_id: int, db: Session = Depends(get_db)):
    material = db.get(Material, material_id)
    if material is None:
        raise HTTPException(404, "教材が見つかりません")
    db.delete(material)
    db.commit()
    return {"ok": True}
