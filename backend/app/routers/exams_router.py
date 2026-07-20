"""予想問題 (exam) 生成 / 改訂 / 追加質問 API。"""
from __future__ import annotations

import json

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


def _normalize_questions(data) -> list[dict]:
    """LLM 応答から [{problem, answer, explanation, followups}] を整形する。"""
    items = data.get("questions", []) if isinstance(data, dict) else data
    out: list[dict] = []
    for q in items or []:
        problem = str(q.get("problem", "")).strip()
        if not problem:
            continue
        out.append(
            {
                "problem": problem,
                "answer": str(q.get("answer", "")).strip(),
                "explanation": str(q.get("explanation", "")).strip(),
                "followups": [],
            }
        )
    return out


def _build_content_md(questions: list[dict]) -> str:
    """印刷/後方互換用の結合 Markdown を組み立てる。"""
    parts = []
    for i, q in enumerate(questions, 1):
        parts.append(
            f"## 問{i}\n\n{q['problem']}\n\n"
            f"**解答:** {q['answer']}\n\n**解説:** {q['explanation']}"
        )
    return "\n\n".join(parts)


def _generate(db: Session, history: list[dict], ctx: str) -> list[dict]:
    messages = prompts.exam_messages(history, ctx, _budget(db))
    data = llm.chat_json(db, messages, temperature=0.6)
    questions = _normalize_questions(data)
    if not questions:
        raise HTTPException(400, "予想問題を生成できませんでした")
    return questions


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
    questions = _generate(db, history, ctx)
    exam = ExamDoc(
        course_id=payload.course_id,
        title=payload.title or "予想問題",
        content_md=_build_content_md(questions),
        questions=questions,
        messages=history
        + [{"role": "assistant", "content": json.dumps({"questions": questions}, ensure_ascii=False)}],
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
    questions = _generate(db, history, ctx)
    exam.questions = questions
    exam.content_md = _build_content_md(questions)
    exam.messages = history + [
        {"role": "assistant", "content": json.dumps({"questions": questions}, ensure_ascii=False)}
    ]
    db.commit()
    db.refresh(exam)
    return exam


@router.post("/{exam_id}/questions/{index}/ask", response_model=schemas.ExamOut)
def ask_followup(
    exam_id: int,
    index: int,
    payload: schemas.ExamAskIn,
    db: Session = Depends(get_db),
):
    """特定の設問への追加質問。回答をその設問の followups に追記する。"""
    exam = db.get(ExamDoc, exam_id)
    if exam is None:
        raise HTTPException(404, "予想問題が見つかりません")
    questions = list(exam.questions or [])
    if index < 0 or index >= len(questions):
        raise HTTPException(404, "設問が見つかりません")
    question = str(payload.question).strip()
    if not question:
        raise HTTPException(400, "質問を入力してください")

    q = dict(questions[index])
    followups = list(q.get("followups", []))
    messages = prompts.exam_followup_messages(q, followups, question)
    answer = llm.chat(db, messages, temperature=0.3)

    q["followups"] = followups + [
        {"role": "user", "content": question},
        {"role": "assistant", "content": answer.strip()},
    ]
    questions[index] = q
    exam.questions = questions  # 再代入して変更を検知させる
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
