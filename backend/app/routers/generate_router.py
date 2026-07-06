"""教材からのカード下書き生成 (プレビュー用、保存はしない)。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import context, llm, prompts, schemas
from ..db import get_db

router = APIRouter(prefix="/api/generate", tags=["generate"])


def _budget(db: Session) -> int:
    try:
        return int(llm.get_setting(db, "context_char_budget"))
    except ValueError:
        return 12000


@router.post("/flashcards", response_model=list[schemas.CardDraft])
def generate_flashcards(payload: schemas.GenerateIn, db: Session = Depends(get_db)):
    ctx = context.gather_context(db, payload.material_ids, payload.course_id)
    if not ctx.strip():
        raise HTTPException(400, "対象教材の文字起こしが見つかりません")
    messages = prompts.flashcards_messages(
        ctx, payload.instruction, _budget(db), payload.count
    )
    data = llm.chat_json(db, messages)
    cards = data.get("cards", []) if isinstance(data, dict) else data
    out = []
    for c in cards:
        front = str(c.get("front", "")).strip()
        back = str(c.get("back", "")).strip()
        if front and back:
            out.append(schemas.CardDraft(front=front, back=back))
    return out
