"""OpenAI 互換 LLM クライアント。

- base_url / api_key / モデルは DB の settings から取得 (無ければ env 既定値)。
- 構造化出力はプロンプトで JSON を指示し、コードフェンス除去 + 失敗時 1 回リトライ。
- LLM_MOCK=1 なら外部通信せず決め打ち応答を返す (E2E 検証用)。
"""
from __future__ import annotations

import base64
import json
import re
from typing import Any

from openai import OpenAI

from .config import settings


# --- 設定アクセス ---------------------------------------------------------

DEFAULTS = {
    "api_base_url": settings.default_api_base_url,
    "api_key": settings.default_api_key,
    "vision_model": settings.default_vision_model,
    "text_model": settings.default_text_model,
    "new_per_day": "20",
    "desired_retention": "0.9",
    "context_char_budget": "12000",
}


def get_setting(db, key: str) -> str:
    from .models import Setting

    row = db.get(Setting, key)
    if row is not None and row.value != "":
        return row.value
    return DEFAULTS.get(key, "")


def set_setting(db, key: str, value: str) -> None:
    from .models import Setting

    row = db.get(Setting, key)
    if row is None:
        row = Setting(key=key, value=value)
        db.add(row)
    else:
        row.value = value


def _client(db) -> OpenAI:
    base_url = get_setting(db, "api_base_url")
    api_key = get_setting(db, "api_key") or "not-needed"
    return OpenAI(base_url=base_url, api_key=api_key, timeout=120.0)


# --- モック応答 -----------------------------------------------------------


def _mock_response(messages: list[dict], want_json: bool) -> str:
    """呼び出し文脈から妥当なダミー応答を生成する。"""
    text = " ".join(
        part.get("text", "")
        for m in messages
        for part in (
            m["content"] if isinstance(m["content"], list) else [{"text": m["content"]}]
        )
        if isinstance(part, dict)
    ).lower()

    if "追加質問" in text or "チューター" in text:
        return "ご質問ありがとうございます。この問題のポイントは、定義を正確に押さえることです。(モック回答)"
    if "予想問題" in text or '"problem"' in text:
        return json.dumps(
            {
                "questions": [
                    {
                        "problem": "水の化学式を答えよ。",
                        "answer": "H2O",
                        "explanation": "水は水素2原子と酸素1原子から成る。",
                    },
                    {
                        "problem": "光合成が行われる細胞小器官を答えよ。",
                        "answer": "葉緑体",
                        "explanation": "光合成は葉緑体のチラコイドで行われる。",
                    },
                ]
            },
            ensure_ascii=False,
        )
    if "flashcard" in text or "フラッシュカード" in text or '"front"' in text:
        return json.dumps(
            {
                "cards": [
                    {"front": "光合成が起こる細胞小器官は?", "back": "葉緑体"},
                    {"front": "水の化学式は?", "back": "H2O"},
                ]
            },
            ensure_ascii=False,
        )
    if "quiz" in text or "クイズ" in text or '"questions"' in text:
        return json.dumps(
            {
                "questions": [
                    {
                        "type": "mcq",
                        "question": "水の化学式は?",
                        "choices": ["H2O", "CO2", "O2", "NaCl"],
                        "answer": "0",
                        "explanation": "水は水素2つと酸素1つから成る。",
                    },
                    {
                        "type": "tf",
                        "question": "光合成は葉緑体で行われる。",
                        "choices": [],
                        "answer": "true",
                        "explanation": "光合成は葉緑体で行われる。",
                    },
                    {
                        "type": "short",
                        "question": "光合成でできる気体は?",
                        "choices": [],
                        "answer": "酸素",
                        "explanation": "光合成では酸素が発生する。",
                    },
                ]
            },
            ensure_ascii=False,
        )
    if "grade" in text or "採点" in text or "judge" in text:
        return json.dumps(
            {"correct": True, "feedback": "正解です。"}, ensure_ascii=False
        )
    # OCR (画像あり) など: markdown テキスト
    return "# サンプル講義ノート\n\n光合成は葉緑体で行われ、水 (H2O) と二酸化炭素から酸素を生成する。"


# --- パブリック API -------------------------------------------------------


def chat(
    db,
    messages: list[dict],
    *,
    model: str | None = None,
    vision: bool = False,
    want_json: bool = False,
    temperature: float = 0.4,
) -> str:
    if settings.llm_mock:
        return _mock_response(messages, want_json)

    model_name = model or get_setting(db, "vision_model" if vision else "text_model")
    client = _client(db)
    resp = client.chat.completions.create(
        model=model_name,
        messages=messages,  # type: ignore[arg-type]
        temperature=temperature,
    )
    return resp.choices[0].message.content or ""


def chat_json(db, messages: list[dict], **kwargs: Any) -> Any:
    """JSON 応答を要求し dict/list にパースして返す。失敗時 1 回リトライ。"""
    kwargs["want_json"] = True
    raw = chat(db, messages, **kwargs)
    parsed = _try_parse_json(raw)
    if parsed is not None:
        return parsed
    # リトライ: 直前の出力を提示し JSON のみ返すよう促す
    retry = messages + [
        {"role": "assistant", "content": raw},
        {
            "role": "user",
            "content": "有効な JSON のみを返してください。前後の説明やコードフェンスは不要です。",
        },
    ]
    raw2 = chat(db, retry, **kwargs)
    parsed2 = _try_parse_json(raw2)
    if parsed2 is None:
        raise ValueError(f"LLM から有効な JSON を取得できませんでした: {raw2[:200]}")
    return parsed2


def _try_parse_json(raw: str) -> Any | None:
    if not raw:
        return None
    text = raw.strip()
    # ```json ... ``` フェンス除去
    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 最初の { または [ から末尾の対応する括弧までを抽出
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start = text.find(open_ch)
        end = text.rfind(close_ch)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    return None


def image_data_uri(image_bytes: bytes, mime: str = "image/jpeg") -> str:
    b64 = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{mime};base64,{b64}"


def list_models(db) -> list[str]:
    """接続テスト: /models を叩いてモデル ID 一覧を返す。"""
    if settings.llm_mock:
        return ["mock/vision", "mock/text"]
    client = _client(db)
    models = client.models.list()
    return sorted(m.id for m in models.data)
