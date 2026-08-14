"""AI 判定・チューター Q&A API (pages/study.html 学習フロー用)。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import llm, prompts
from ..db import get_db

router = APIRouter(prefix="/api/ai", tags=["ai"])


class GradeIn(BaseModel):
    question: str = ""
    model_answer: str = ""
    user_answer: str = ""


class TutorIn(BaseModel):
    question: str = ""
    model_answer: str = ""
    user_answer: str = ""
    user_question: str = ""
    history: list[dict] = []


class PlanIn(BaseModel):
    test_days: int = 14
    nodes: list[dict] = []
    materials: list[dict] = []  # 過去問 {title, year, exam_type}


class PlanChatIn(BaseModel):
    test_days: int = 14
    nodes: list[dict] = []
    history: list[dict] = []
    materials: list[dict] = []  # 過去問 {title, year, exam_type}


@router.post("/grade")
def grade(payload: GradeIn, db: Session = Depends(get_db)) -> dict:
    """短答式の解答を LLM で採点する。失敗時は完全一致でフォールバック。"""
    try:
        data = llm.chat_json(
            db,
            prompts.grade_short_messages(
                payload.question, payload.model_answer, payload.user_answer
            ),
            temperature=0.0,
        )
        return {
            "correct": bool(data.get("correct", False)),
            "feedback": str(data.get("feedback", "")),
        }
    except Exception:  # noqa: BLE001
        correct = payload.user_answer.strip() == payload.model_answer.strip()
        return {
            "correct": correct,
            "feedback": "AI 判定に失敗したため完全一致で判定しました。",
        }


@router.post("/tutor")
def tutor(payload: TutorIn, db: Session = Depends(get_db)) -> dict:
    """設問に対する追加質問にチューターとして答える。"""
    try:
        messages = prompts.tutor_messages(
            payload.question,
            payload.model_answer,
            payload.user_answer,
            payload.user_question,
            payload.history,
        )
        return {"answer": llm.chat(db, messages, temperature=0.3)}
    except Exception:  # noqa: BLE001
        return {"answer": "AI と接続できませんでした。もう一度お試しください。"}


@router.post("/plan")
def plan(payload: PlanIn, db: Session = Depends(get_db)) -> dict:
    """テスト逆算で日割り学習プランを提案する。"""
    try:
        data = llm.chat_json(
            db,
            prompts.plan_messages(
                payload.test_days,
                payload.nodes,
                payload.materials,
                study_method=llm.get_setting(db, "study_method"),
            ),
            temperature=0.4,
        )
        plan_list = data.get("plan", [])
        if not isinstance(plan_list, list):
            plan_list = []
        return {
            "plan": plan_list,
            "summary": str(data.get("summary", "")),
        }
    except Exception:  # noqa: BLE001
        return {"plan": [], "summary": "AI プラン提案に失敗しました。"}


@router.post("/plan_chat")
def plan_chat(payload: PlanChatIn, db: Session = Depends(get_db)) -> dict:
    """プラン相談チャット。会話に応じて日割りプランを調整する。"""
    try:
        data = llm.chat_json(
            db,
            prompts.plan_chat_messages(
                payload.test_days,
                payload.nodes,
                payload.history,
                payload.materials,
                study_method=llm.get_setting(db, "study_method"),
            ),
            temperature=0.5,
        )
        plan_list = data.get("plan", [])
        if not isinstance(plan_list, list):
            plan_list = []
        return {
            "message": str(data.get("message", "")),
            "plan": plan_list,
            "summary": str(data.get("summary", "")),
        }
    except Exception:  # noqa: BLE001
        return {"message": "AI と接続できませんでした。もう一度お試しください。", "plan": [], "summary": ""}