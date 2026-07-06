"""LLM の JSON 抽出堅牢性テスト。"""
from app.llm import _try_parse_json


def test_plain_json():
    assert _try_parse_json('{"a": 1}') == {"a": 1}


def test_fenced_json():
    raw = '```json\n{"a": 1}\n```'
    assert _try_parse_json(raw) == {"a": 1}


def test_json_with_prose():
    raw = 'はい、以下が結果です:\n{"cards": [{"front": "x", "back": "y"}]}\n以上です。'
    assert _try_parse_json(raw) == {"cards": [{"front": "x", "back": "y"}]}


def test_array_extraction():
    raw = "先頭の説明 [1, 2, 3] 末尾"
    assert _try_parse_json(raw) == [1, 2, 3]


def test_invalid_returns_none():
    assert _try_parse_json("これは JSON ではありません") is None
