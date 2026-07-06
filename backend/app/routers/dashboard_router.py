"""ダッシュボード集計 API。"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Card, Deck, Material, Quiz, ReviewLog

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
def dashboard(db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    due_today = (
        db.scalar(
            select(func.count(Card.id)).where(
                Card.suspended.is_(False),
                Card.is_new.is_(False),
                Card.due <= now,
            )
        )
        or 0
    )
    new_cards = (
        db.scalar(
            select(func.count(Card.id)).where(
                Card.suspended.is_(False), Card.is_new.is_(True)
            )
        )
        or 0
    )
    reviewed_today = (
        db.scalar(
            select(func.count(ReviewLog.id)).where(ReviewLog.reviewed_at >= start)
        )
        or 0
    )
    counts = {
        "materials": db.scalar(select(func.count(Material.id))) or 0,
        "decks": db.scalar(select(func.count(Deck.id))) or 0,
        "cards": db.scalar(select(func.count(Card.id))) or 0,
        "quizzes": db.scalar(select(func.count(Quiz.id))) or 0,
    }
    recent = db.scalars(
        select(Material).order_by(Material.created_at.desc()).limit(5)
    ).all()
    return {
        "due_today": due_today,
        "new_cards": new_cards,
        "reviewed_today": reviewed_today,
        "counts": counts,
        "recent_materials": [
            {
                "id": m.id,
                "title": m.title,
                "status": m.status,
                "kind": m.kind,
            }
            for m in recent
        ],
    }
