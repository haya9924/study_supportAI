"""予想問題 (exam) 生成 / 改訂 API。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import context, llm, prompts, schemas
from ..db import get_db
from ..models import ExamDoc

router = APIRouter(prefix="/api/exams", tags=["exams"])


def _budget(db: Session) -> int:
    try:
        return int(llm.get_setting(db, "context_char_budget"))
    except ValueError:
        return 12000


@router.get("", response_model=list[schemas.ExamOut])
def list_exams(course_id: int | None = None, db: Session = Depends(get_db)):
    stmt = select(ExamDoc).order_by(ExamDoc.created_at.desc())
    if course_id is not None:
        stmt = stmt.where(ExamDoc.course_id == course_id)
    return db.scalars(stmt).all()


@router.get("/{exam_id}", response_model=schemas.ExamOut)
def get_exam(exam_id: int, db: Session = Depends(get_db)):
    exam = db.get(ExamDoc, exam_id)
    if exam is None:
        raise HTTPException(404, "予想問題が見つかりません")
    return exam


@router.post("", response_model=schemas.ExamOut)
def create_exam(payload: schemas.GenerateIn, db: Session = Depends(get_db)):
    ctx = context.gather_context(db, payload.material_ids, payload.course_id)
    if not ctx.strip():
        raise HTTPException(400, "対象教材の文字起こしが見つかりません")
    instruction = payload.instruction or "過去問の傾向に沿った予想問題を作成してください。"
    history = [{"role": "user", "content": instruction}]
    messages = prompts.exam_messages(history, ctx, _budget(db))
    content = llm.chat(db, messages, temperature=0.6)
    exam = ExamDoc(
        course_id=payload.course_id,
        title=payload.title or "予想問題",
        content_md=content,
        messages=history + [{"role": "assistant", "content": content}],
        source_material_ids=payload.material_ids,
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return exam


@router.post("/{exam_id}/revise", response_model=schemas.ExamOut)
def revise_exam(
    exam_id: int, payload: schemas.ExamReviseIn, db: Session = Depends(get_db)
):
    exam = db.get(ExamDoc, exam_id)
    if exam is None:
        raise HTTPException(404, "予想問題が見つかりません")
    ctx = context.gather_context(db, exam.source_material_ids, exam.course_id)
    history = list(exam.messages) + [{"role": "user", "content": payload.instruction}]
    messages = prompts.exam_messages(history, ctx, _budget(db))
    content = llm.chat(db, messages, temperature=0.6)
    exam.content_md = content
    exam.messages = history + [{"role": "assistant", "content": content}]
    db.commit()
    db.refresh(exam)
    return exam


@router.delete("/{exam_id}")
def delete_exam(exam_id: int, db: Session = Depends(get_db)):
    exam = db.get(ExamDoc, exam_id)
    if exam is None:
        raise HTTPException(404, "予想問題が見つかりません")
    db.delete(exam)
    db.commit()
    return {"ok": True}
