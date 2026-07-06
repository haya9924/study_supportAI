"""FSRS ラッパの単体テスト。"""
from datetime import datetime, timezone, timedelta

from app import srs


def test_new_card_state_has_fields():
    state = srs.new_card_state()
    assert "due" in state
    assert "stability" in state


def test_review_advances_due():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    state = srs.new_card_state()
    new_state, due = srs.review(state, 3, now=now)  # Good
    assert due >= now
    assert new_state != state


def test_again_shorter_than_easy():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    state = srs.new_card_state()
    _, due_again = srs.review(state, 1, now=now)
    _, due_easy = srs.review(state, 4, now=now)
    # Again は Easy より早く再表示される
    assert due_again < due_easy


def test_preview_intervals_all_ratings():
    intervals = srs.preview_intervals(srs.new_card_state())
    assert set(intervals.keys()) == {1, 2, 3, 4}
    assert all(isinstance(v, str) and v for v in intervals.values())


def test_repeated_good_grows_interval():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    state = srs.new_card_state()
    # Good を繰り返すと間隔が伸びていく
    _, due1 = srs.review(state, 3, now=now)
    state2, _ = srs.review(state, 3, now=now)
    _, due2 = srs.review(state2, 3, now=due1 + timedelta(days=1))
    assert (due2 - now) > (due1 - now)
