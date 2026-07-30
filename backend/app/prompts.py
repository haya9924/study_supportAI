"""LLM 用プロンプト組み立て。"""
from __future__ import annotations

from .llm import image_data_uri


def ocr_messages(image_bytes: bytes) -> list[dict]:
    system = (
        "あなたは講義資料やスライド、試験問題を正確に文字起こしする OCR アシスタントです。"
        "画像の内容を、見出し・箇条書き・表などの構造を保った Markdown で書き起こしてください。"
        "数式は LaTeX ($...$ もしくは $$...$$) で表現します。"
        "図やグラフは [図: 簡単な説明] のように短く記述します。"
        "画像に無い内容を創作しないでください。説明や前置きは不要で、書き起こし本文のみを返してください。"
    )
    return [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "この画像を Markdown で文字起こししてください。"},
                {
                    "type": "image_url",
                    "image_url": {"url": image_data_uri(image_bytes)},
                },
            ],
        },
    ]


def _context_block(context: str, budget: int) -> str:
    if len(context) > budget:
        context = context[:budget] + "\n...(以下略)"
    return context


def flashcards_messages(context: str, instruction: str, budget: int, n: int) -> list[dict]:
    system = (
        "あなたは学習用フラッシュカードを作成する教育アシスタントです。"
        "与えられた教材から、暗記に適した表裏 (front/back) 形式のカードを作成します。"
        "front は問い、back は簡潔な答え。1 枚 1 概念にします。"
        '出力は JSON のみ: {"cards": [{"front": "...", "back": "..."}]} 。'
    )
    user = (
        f"以下の教材から日本語のフラッシュカードを最大{n}枚作成してください。\n"
        f"追加指示: {instruction or 'なし'}\n\n--- 教材 ---\n"
        + _context_block(context, budget)
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def quiz_messages(context: str, instruction: str, budget: int, n: int) -> list[dict]:
    system = (
        "あなたは学習用クイズを作成する教育アシスタントです。"
        "教材から、選択式(mcq)・正誤(tf)・短答(short)を織り交ぜた設問を作成します。"
        "出力は JSON のみ: "
        '{"questions": [{"type": "mcq|tf|short", "question": "...", '
        '"choices": ["...", ...], "answer": "...", "explanation": "..."}]} 。'
        "mcq の answer は正解の選択肢インデックス(0始まり)の文字列、choices は 3〜4 個。"
        "tf の answer は \"true\" か \"false\"、choices は空配列。"
        "short の answer は模範解答の文字列、choices は空配列。"
    )
    user = (
        f"以下の教材から日本語のクイズを最大{n}問作成してください。\n"
        f"追加指示: {instruction or 'なし'}\n\n--- 教材 ---\n"
        + _context_block(context, budget)
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def grade_short_messages(question: str, model_answer: str, user_answer: str) -> list[dict]:
    system = (
        "あなたは短答式解答を採点する教育アシスタントです。"
        "模範解答と照らし、意味が合っていれば正解とします(表記ゆれや言い回しの違いは許容)。"
        '出力は JSON のみ: {"correct": true|false, "feedback": "短い日本語の講評"} 。'
    )
    user = (
        f"設問: {question}\n模範解答: {model_answer}\n"
        f"受験者の解答: {user_answer}\n\nこの解答を採点(grade)してください。"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _exam_context_block(
    past_exam: str, test_info: str, reference: str, budget: int
) -> str:
    """種別ごとにラベル付けした参考情報ブロックを作る。

    過去問・テスト情報は優先して全文含め、参考資料を残り予算で切り詰める。
    """
    sections: list[str] = []
    if past_exam.strip():
        sections.append(
            "--- 過去問(この出題形式・大問構成・配点・難易度・言い回しを忠実に踏襲すること) ---\n"
            + past_exam
        )
    if test_info.strip():
        sections.append(
            "--- テスト情報(今回のテストの出題範囲・形式の指定。これに厳密に従って作問すること) ---\n"
            + test_info
        )
    remaining = max(2000, budget - len(past_exam) - len(test_info))
    ref = _context_block(reference, remaining)
    if ref.strip():
        sections.append("--- 参考資料(講義資料など) ---\n" + ref)
    return "\n\n".join(sections) or "(参考情報なし)"


def exam_messages(
    history: list[dict],
    past_exam: str,
    test_info: str,
    reference: str,
    budget: int,
) -> list[dict]:
    """予想問題(JSON構造化)の生成/改訂。history は過去の指示 (role/content)。"""
    system = (
        "あなたは大学の試験の予想問題を作成する専門家です。"
        "提供された過去問・テスト情報・講義資料をもとに、本番を想定した予想問題を作成します。"
        "【過去問】が与えられた場合は、その出題形式・大問構成・設問数・配点・難易度・"
        "言い回しをできる限り忠実に踏襲してください。"
        "【テスト情報】が与えられた場合は、そこに書かれた出題範囲・形式・条件に厳密に従って作問してください。"
        "各設問について、問題文・模範解答・解説を分けて出力してください。"
        "数式は LaTeX ($...$) で記述します。"
        "出力は JSON のみ: "
        '{"questions": [{"problem": "問題文(Markdown)", '
        '"answer": "模範解答(Markdown)", "explanation": "解説(Markdown)"}]} 。'
        "problem には解答や解説を含めないでください。"
    )
    ctx = _exam_context_block(past_exam, test_info, reference, budget)
    messages = [{"role": "system", "content": system}]
    # 最初のユーザーメッセージに参考情報を添付
    first = True
    for h in history:
        if first and h["role"] == "user":
            messages.append(
                {"role": "user", "content": f"{h['content']}\n\n{ctx}"}
            )
            first = False
        else:
            messages.append({"role": h["role"], "content": h["content"]})
    return messages


def exam_followup_messages(
    question: dict, history: list[dict], user_question: str
) -> list[dict]:
    """予想問題の特定の設問に対する学習者の追加質問に答える。"""
    system = (
        "あなたは学習者を助けるチューターです。"
        "以下の問題・模範解答・解説を踏まえ、学習者の追加質問に日本語で分かりやすく答えます。"
        "数式は LaTeX ($...$) で記述します。"
    )
    ctx = (
        f"問題:\n{question.get('problem', '')}\n\n"
        f"模範解答:\n{question.get('answer', '')}\n\n"
        f"解説:\n{question.get('explanation', '')}"
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": ctx},
    ]
    for f in history:
        messages.append({"role": f["role"], "content": f["content"]})
    messages.append({"role": "user", "content": user_question})
    return messages
