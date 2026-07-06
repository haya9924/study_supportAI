"""py-fsrs (FSRS) ラッパ。カード状態のシリアライズと復習キューを扱う。"""
from __future__ import annotations

from datetime import datetime, timezone

from fsrs import Scheduler, Card as FsrsCard, Rating

RATINGS = {1: Rating.Again, 2: Rating.Hard, 3: Rating.Good, 4: Rating.Easy}


def _scheduler(desired_retention: float = 0.9) -> Scheduler:
    return Scheduler(desired_retention=desired_retention)


def new_card_state() -> dict:
    """新規カードの初期 FSRS 状態を返す。"""
    return FsrsCard().to_dict()


def _load(state: dict) -> FsrsCard:
    if not state:
        return FsrsCard()
    return FsrsCard.from_dict(state)


def review(
    state: dict, rating: int, *, desired_retention: float = 0.9, now: datetime | None = None
) -> tuple[dict, datetime]:
    """レーティングを適用し、新しい状態と次回 due を返す。"""
    now = now or datetime.now(timezone.utc)
    card = _load(state)
    sched = _scheduler(desired_retention)
    card2, _log = sched.review_card(card, RATINGS[rating], review_datetime=now)
    return card2.to_dict(), card2.due


def preview_intervals(
    state: dict, *, desired_retention: float = 0.9, now: datetime | None = None
) -> dict[int, str]:
    """各レーティングを押した場合の次回 due を人間可読な文字列で返す。"""
    now = now or datetime.now(timezone.utc)
    out: dict[int, str] = {}
    for r in (1, 2, 3, 4):
        card = _load(state)
        sched = _scheduler(desired_retention)
        card2, _ = sched.review_card(card, RATINGS[r], review_datetime=now)
        out[r] = _format_delta(card2.due - now)
    return out


def _format_delta(delta) -> str:
    secs = max(0, int(delta.total_seconds()))
    mins = secs // 60
    if mins < 60:
        return f"{max(1, mins)}分"
    hours = mins // 60
    if hours < 24:
        return f"{hours}時間"
    days = hours // 24
    if days < 30:
        return f"{days}日"
    months = days // 30
    if months < 12:
        return f"{months}ヶ月"
    return f"{days // 365}年"
