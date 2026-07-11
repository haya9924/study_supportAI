"""デッキ / フラッシュカード / FSRS 復習 API。"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import llm, schemas, srs
from ..db import get_db
from ..models import Card, Deck, ReviewLog

router = APIRouter(prefix="/api/decks", tags=["decks"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _retention(db: Session) -> float:
    try:
        return float(llm.get_setting(db, "desired_retention"))
    except ValueError:
        return 0.9


def _new_studied_today(db: Session, deck_id: int) -> int:
    """本日(UTC)この デッキで学習した新規カード数。"""
    start = _now().replace(hour=0, minute=0, second=0, microsecond=0)
    return (
        db.scalar(
            select(func.count(ReviewLog.id)).where(
                ReviewLog.deck_id == deck_id,
                ReviewLog.was_new.is_(True),
                ReviewLog.reviewed_at >= start,
            )
        )
        or 0
    )


def _deck_counts(db: Session, deck: Deck) -> tuple[int, int, int]:
    """(total, due_count, new_available) を返す。"""
    now = _now()
    total = (
        db.scalar(select(func.count(Card.id)).where(Card.deck_id == deck.id)) or 0
    )
    due_count = (
        db.scalar(
            select(func.count(Card.id)).where(
                Card.deck_id == deck.id,
                Card.suspended.is_(False),
                Card.is_new.is_(False),
                Card.due <= now,
            )
        )
        or 0
    )
    new_total = (
        db.scalar(
            select(func.count(Card.id)).where(
                Card.deck_id == deck.id,
                Card.suspended.is_(False),
                Card.is_new.is_(True),
            )
        )
        or 0
    )
    new_available = max(
        0, min(new_total, deck.new_per_day - _new_studied_today(db, deck.id))
    )
    return total, due_count, new_available


@router.get("", response_model=list[schemas.DeckStats])
def list_decks(db: Session = Depends(get_db)):
    decks = db.scalars(select(Deck).order_by(Deck.created_at.desc())).all()
    out = []
    for d in decks:
        total, due, new_av = _deck_counts(db, d)
        out.append(
            schemas.DeckStats(
                id=d.id,
                name=d.name,
                course_id=d.course_id,
                new_per_day=d.new_per_day,
                created_at=d.created_at,
                total=total,
                due_count=due,
                new_count=new_av,
            )
        )
    return out


@router.post("", response_model=schemas.DeckOut)
def create_deck(payload: schemas.DeckIn, db: Session = Depends(get_db)):
    deck = Deck(
        name=payload.name.strip() or "無題のデッキ",
        course_id=payload.course_id,
        new_per_day=payload.new_per_day,
    )
    db.add(deck)
    db.commit()
    db.refresh(deck)
    return deck


@router.put("/{deck_id}", response_model=schemas.DeckOut)
def update_deck(
    deck_id: int, payload: schemas.DeckUpdateIn, db: Session = Depends(get_db)
):
    deck = db.get(Deck, deck_id)
    if deck is None:
        raise HTTPException(404, "デッキが見つかりません")
    if payload.name is not None and payload.name.strip():
        deck.name = payload.name.strip()
    if payload.new_per_day is not None:
        deck.new_per_day = payload.new_per_day
    db.commit()
    db.refresh(deck)
    return deck


@router.delete("/{deck_id}")
def delete_deck(deck_id: int, db: Session = Depends(get_db)):
    deck = db.get(Deck, deck_id)
    if deck is None:
        raise HTTPException(404, "デッキが見つかりません")
    db.delete(deck)
    db.commit()
    return {"ok": True}


@router.get("/{deck_id}/cards", response_model=list[schemas.CardOut])
def list_cards(deck_id: int, db: Session = Depends(get_db)):
    return db.scalars(
        select(Card).where(Card.deck_id == deck_id).order_by(Card.created_at.desc())
    ).all()


@router.post("/{deck_id}/cards", response_model=schemas.CardOut)
def add_card(deck_id: int, payload: schemas.CardIn, db: Session = Depends(get_db)):
    deck = db.get(Deck, deck_id)
    if deck is None:
        raise HTTPException(404, "デッキが見つかりません")
    card = Card(
        deck_id=deck_id,
        front=payload.front,
        back=payload.back,
        due=_now(),
        fsrs_state=srs.new_card_state(),
        is_new=True,
    )
    db.add(card)
    db.commit()
    db.refresh(card)
    return card


@router.post("/{deck_id}/cards/bulk", response_model=list[schemas.CardOut])
def add_cards_bulk(
    deck_id: int, payload: schemas.AddCardsIn, db: Session = Depends(get_db)
):
    deck = db.get(Deck, deck_id)
    if deck is None:
        raise HTTPException(404, "デッキが見つかりません")
    created = []
    for c in payload.cards:
        card = Card(
            deck_id=deck_id,
            front=c.front,
            back=c.back,
            due=_now(),
            fsrs_state=srs.new_card_state(),
            is_new=True,
        )
        db.add(card)
        created.append(card)
    db.commit()
    for c in created:
        db.refresh(c)
    return created


@router.put("/cards/{card_id}", response_model=schemas.CardOut)
def update_card(card_id: int, payload: schemas.CardIn, db: Session = Depends(get_db)):
    card = db.get(Card, card_id)
    if card is None:
        raise HTTPException(404, "カードが見つかりません")
    card.front = payload.front
    card.back = payload.back
    db.commit()
    db.refresh(card)
    return card


@router.delete("/cards/{card_id}")
def delete_card(card_id: int, db: Session = Depends(get_db)):
    card = db.get(Card, card_id)
    if card is None:
        raise HTTPException(404, "カードが見つかりません")
    db.delete(card)
    db.commit()
    return {"ok": True}


def _pick_next_card(db: Session, deck: Deck) -> Card | None:
    """復習キューから次の 1 枚を選ぶ。期限到来カード優先、次に新規(上限内)。"""
    now = _now()
    due = db.scalar(
        select(Card)
        .where(
            Card.deck_id == deck.id,
            Card.suspended.is_(False),
            Card.is_new.is_(False),
            Card.due <= now,
        )
        .order_by(Card.due)
    )
    if due is not None:
        return due
    _total, _due_count, new_available = _deck_counts(db, deck)
    if new_available > 0:
        return db.scalar(
            select(Card)
            .where(
                Card.deck_id == deck.id,
                Card.suspended.is_(False),
                Card.is_new.is_(True),
            )
            .order_by(Card.created_at)
        )
    return None


@router.get("/{deck_id}/next", response_model=schemas.ReviewCardOut)
def next_card(deck_id: int, db: Session = Depends(get_db)):
    deck = db.get(Deck, deck_id)
    if deck is None:
        raise HTTPException(404, "デッキが見つかりません")
    card = _pick_next_card(db, deck)
    _total, due_count, new_available = _deck_counts(db, deck)
    if card is None:
        return schemas.ReviewCardOut(
            card=None, intervals=None, remaining=0, new_remaining=0
        )
    intervals = srs.preview_intervals(
        card.fsrs_state, desired_retention=_retention(db)
    )
    return schemas.ReviewCardOut(
        card=schemas.CardOut.model_validate(card),
        intervals=intervals,
        remaining=due_count + new_available,
        new_remaining=new_available,
    )


@router.post("/cards/{card_id}/review", response_model=schemas.ReviewCardOut)
def review_card(
    card_id: int, payload: schemas.ReviewIn, db: Session = Depends(get_db)
):
    if payload.rating not in (1, 2, 3, 4):
        raise HTTPException(400, "rating は 1〜4 です")
    card = db.get(Card, card_id)
    if card is None:
        raise HTTPException(404, "カードが見つかりません")
    now = _now()
    # 取り消し用に復習直前の状態をスナップショット
    prev_state = card.fsrs_state
    prev_due = card.due
    prev_reps = card.reps
    was_new = card.is_new

    new_state, due = srs.review(
        card.fsrs_state, payload.rating, desired_retention=_retention(db), now=now
    )
    card.fsrs_state = new_state
    card.due = due
    card.reps += 1
    card.is_new = False
    db.add(
        ReviewLog(
            card_id=card.id,
            deck_id=card.deck_id,
            rating=payload.rating,
            was_new=was_new,
            reviewed_at=now,
            prev_fsrs_state=prev_state,
            prev_due=prev_due,
            prev_reps=prev_reps,
            prev_is_new=was_new,
        )
    )
    db.commit()

    # 次のカードを返す (途中再開はサーバー状態から常に再計算されるため自動的に機能)
    return next_card(card.deck_id, db)


def _review_card_out(db: Session, deck: Deck, card: Card) -> schemas.ReviewCardOut:
    _total, due_count, new_available = _deck_counts(db, deck)
    intervals = srs.preview_intervals(
        card.fsrs_state, desired_retention=_retention(db)
    )
    return schemas.ReviewCardOut(
        card=schemas.CardOut.model_validate(card),
        intervals=intervals,
        remaining=due_count + new_available,
        new_remaining=new_available,
    )


@router.post("/{deck_id}/undo", response_model=schemas.ReviewCardOut)
def undo_review(deck_id: int, db: Session = Depends(get_db)):
    """直近の復習を取り消し、そのカードを復習直前の状態に戻して現在のカードとして返す。"""
    deck = db.get(Deck, deck_id)
    if deck is None:
        raise HTTPException(404, "デッキが見つかりません")
    log = db.scalar(
        select(ReviewLog)
        .where(ReviewLog.deck_id == deck_id)
        .order_by(ReviewLog.reviewed_at.desc(), ReviewLog.id.desc())
    )
    if log is None:
        raise HTTPException(400, "取り消せる復習履歴がありません")
    card = db.get(Card, log.card_id)
    if card is None:
        db.delete(log)
        db.commit()
        raise HTTPException(400, "対象のカードが見つかりません")
    # スナップショットから復元
    card.fsrs_state = log.prev_fsrs_state or {}
    card.due = log.prev_due or _now()
    card.reps = log.prev_reps or 0
    card.is_new = bool(log.prev_is_new)
    db.delete(log)
    db.commit()
    return _review_card_out(db, deck, card)
