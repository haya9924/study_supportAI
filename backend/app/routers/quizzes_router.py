"""クイズ生成 / 解答 / 採点 API。"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import context, llm, prompts, schemas
from ..db import get_db
from ..models import Quiz, QuizAttempt, QuizQuestion

router = APIRouter(prefix="/api/quizzes", tags=["quizzes"])


def _budget(db: Session) -> int:
    try:
        return int(llm.get_setting(db, "context_char_budget"))
    except ValueError:
        return 12000


@router.get("", response_model=list[schemas.QuizOut])
def list_quizzes(course_id: int | None = None, db: Session = Depends(get_db)):
    stmt = select(Quiz).order_by(Quiz.created_at.desc())
    if course_id is not None:
        stmt = stmt.where(Quiz.course_id == course_id)
    return db.scalars(stmt).all()


@router.post("", response_model=schemas.QuizDetail)
def create_quiz(payload: schemas.GenerateIn, db: Session = Depends(get_db)):
    ctx = context.gather_context(db, payload.material_ids, payload.course_id)
    if not ctx.strip():
        raise HTTPException(400, "対象教材の文字起こしが見つかりません")
    messages = prompts.quiz_messages(
        ctx, payload.instruction, _budget(db), payload.count
    )
    data = llm.chat_json(db, messages)
    questions = data.get("questions", []) if isinstance(data, dict) else data
    if not questions:
        raise HTTPException(400, "問題を生成できませんでした")

    quiz = Quiz(
        course_id=payload.course_id,
        title=payload.title or "クイズ",
        source_material_ids=payload.material_ids,
    )
    db.add(quiz)
    db.flush()
    for i, q in enumerate(questions):
        qtype = q.get("type", "mcq")
        if qtype not in ("mcq", "tf", "short"):
            qtype = "short"
        db.add(
            QuizQuestion(
                quiz_id=quiz.id,
                order_no=i,
                type=qtype,
                question=str(q.get("question", "")),
                choices=q.get("choices", []) or [],
                answer=str(q.get("answer", "")),
                explanation=str(q.get("explanation", "")),
            )
        )
    db.commit()
    db.refresh(quiz)
    return quiz


@router.get("/{quiz_id}", response_model=schemas.QuizDetail)
def get_quiz(quiz_id: int, db: Session = Depends(get_db)):
    quiz = db.get(Quiz, quiz_id)
    if quiz is None:
        raise HTTPException(404, "クイズが見つかりません")
    return quiz


@router.delete("/{quiz_id}")
def delete_quiz(quiz_id: int, db: Session = Depends(get_db)):
    quiz = db.get(Quiz, quiz_id)
    if quiz is None:
        raise HTTPException(404, "クイズが見つかりません")
    db.delete(quiz)
    db.commit()
    return {"ok": True}


@router.post("/{quiz_id}/attempt", response_model=schemas.AttemptOut)
def start_or_resume_attempt(quiz_id: int, db: Session = Depends(get_db)):
    """未完了の解答があれば再開、無ければ新規作成 (途中再開)。"""
    quiz = db.get(Quiz, quiz_id)
    if quiz is None:
        raise HTTPException(404, "クイズが見つかりません")
    attempt = db.scalar(
        select(QuizAttempt)
        .where(QuizAttempt.quiz_id == quiz_id, QuizAttempt.status == "in_progress")
        .order_by(QuizAttempt.started_at.desc())
    )
    if attempt is None:
        attempt = QuizAttempt(quiz_id=quiz_id, status="in_progress", answers={})
        db.add(attempt)
        db.commit()
        db.refresh(attempt)
    return schemas.AttemptOut(
        id=attempt.id,
        quiz_id=attempt.quiz_id,
        status=attempt.status,
        answers=attempt.answers,
        score=attempt.score,
    )


@router.post("/attempt/{attempt_id}/answer")
def submit_answer(
    attempt_id: int, payload: schemas.AttemptAnswerIn, db: Session = Depends(get_db)
):
    """1 問分の解答を採点し即保存する (途中再開のため)。"""
    attempt = db.get(QuizAttempt, attempt_id)
    if attempt is None:
        raise HTTPException(404, "解答が見つかりません")
    question = db.get(QuizQuestion, payload.question_id)
    if question is None or question.quiz_id != attempt.quiz_id:
        raise HTTPException(404, "設問が見つかりません")

    response = payload.response
    correct: bool
    feedback = question.explanation

    if question.type == "mcq":
        correct = str(response).strip() == str(question.answer).strip()
    elif question.type == "tf":
        correct = str(response).strip().lower() == str(question.answer).strip().lower()
    else:  # short: LLM 判定
        try:
            data = llm.chat_json(
                db,
                prompts.grade_short_messages(
                    question.question, question.answer, response
                ),
                temperature=0.0,
            )
            correct = bool(data.get("correct", False))
            feedback = data.get("feedback", "") or question.explanation
        except Exception:  # noqa: BLE001
            # 判定失敗時は完全一致でフォールバック
            correct = response.strip() == question.answer.strip()

    answers = dict(attempt.answers)
    answers[str(question.id)] = {
        "response": response,
        "correct": correct,
        "feedback": feedback,
        "correct_answer": question.answer,
        "type": question.type,
    }
    attempt.answers = answers
    db.commit()
    return {
        "correct": correct,
        "feedback": feedback,
        "correct_answer": question.answer,
        "explanation": question.explanation,
    }


@router.post("/attempt/{attempt_id}/finish", response_model=schemas.AttemptOut)
def finish_attempt(attempt_id: int, db: Session = Depends(get_db)):
    attempt = db.get(QuizAttempt, attempt_id)
    if attempt is None:
        raise HTTPException(404, "解答が見つかりません")
    quiz = db.get(Quiz, attempt.quiz_id)
    total = len(quiz.questions) if quiz else 0
    correct_n = sum(1 for a in attempt.answers.values() if a.get("correct"))
    attempt.score = (correct_n / total * 100.0) if total else 0.0
    attempt.status = "done"
    attempt.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(attempt)
    return schemas.AttemptOut(
        id=attempt.id,
        quiz_id=attempt.quiz_id,
        status=attempt.status,
        answers=attempt.answers,
        score=attempt.score,
    )


@router.get("/{quiz_id}/answers")
def get_answers(quiz_id: int, db: Session = Depends(get_db)):
    """採点結果表示用に正解・解説を返す。"""
    quiz = db.get(Quiz, quiz_id)
    if quiz is None:
        raise HTTPException(404, "クイズが見つかりません")
    return {
        str(q.id): {"answer": q.answer, "explanation": q.explanation, "type": q.type}
        for q in quiz.questions
    }
