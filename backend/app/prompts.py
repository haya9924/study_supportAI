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


def tutor_messages(
    question: str,
    model_answer: str,
    user_answer: str,
    user_question: str,
    history: list[dict],
) -> list[dict]:
    """学習フローの設問に対するチューター Q&A を組み立てる。

    history は過去の Q&A ペア (role/content)。answer の出し惜しみはせず、
    分かりやすく日本語で回答する。
    """
    system = (
        "あなたは学習者を一人ずつ教えるチューターです。"
        "以下の問題と模範解答を踏まえ、学習者の追加質問に日本語で分かりやすく答えます。"
        "質問の意図を汲み、定義や仕組みを噛み砕いて説明します。"
        "数式は LaTeX ($...$) で記述します。"
    )
    ctx = f"問題:\n{question}\n\n模範解答:\n{model_answer}"
    if user_answer.strip():
        ctx += f"\n\n学習者の解答:\n{user_answer}"
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": ctx},
    ]
    for h in history:
        messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
    messages.append({"role": "user", "content": f"追加質問: {user_question}"})
    return messages


def plan_messages(
    test_days: int,
    nodes: list[dict],
    past_exams: list[dict] | None = None,
    study_method: str = "",
) -> list[dict]:
    """テスト逆算の日割り学習プランを提案する。

    nodes: 各ノードの {id, name, type, state, weight}。残りノードと日数から
    実行可能な日割りを組む。
    past_exams: 取り込まれた過去問の {title, year, exam_type}。ある場合は
    「過去問演習」の回をプランに含める。
    study_method: 学習者の学習法・方針。非空なら必ず従う。
    """
    system = (
        "あなたは学習計画を立案する教育コーチです。"
        "テストまでの残り日数と未クリアのノード一覧から、日割り学習プランを提案します。"
        "1 日ごとに消化するノードを割り当て、無理なく全ノードを緑(クリア)まで到達させます。"
        "過去問・予想問題がある場合は、テスト前に「過去問演習」の回を適切に組み込みます。"
        "過去問演習の回は nodes に [過去問演習: タイトル(年度)] の形式で含めます。"
    )
    if study_method.strip():
        system += (
            "\n【学習者の学習法・方針（この方針に必ず従ってプランを組むこと）】\n"
            + study_method.strip()
        )
    system += (
        '出力は JSON のみ: {"plan": [{"day": 1, "nodes": ["ノード名", ...], '
        '"note": "1日の狙い・目安時間"}], "summary": "全体方針の短い説明"} 。'
    )
    node_lines = "\n".join(
        f"- {n.get('name','')} (type={n.get('type','')}, state={n.get('state','')})"
        for n in nodes
    )
    exam_lines = "\n".join(
        f"- {p.get('title','')} (年度 {p.get('year','')}, {p.get('exam_type','')})"
        for p in (past_exams or [])
    )
    user = (
        f"テストまで {test_days} 日。未クリアのノード:\n{node_lines or '(なし)'}\n\n"
        f"過去問:\n{exam_lines or '(なし)'}\n\n"
        "日割りプランを提案してください。"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def plan_nodes_messages(
    test_days: int,
    course_name: str,
    materials: list[dict],
    study_method: str = "",
) -> list[dict]:
    """科目の教材から、学習マップに載せるノード構造を生成する (第1段・設計)。

    光合成マップと同じように、各ノードに type (discovery/basic/practice/
    merge/gate/boss) と内容・依存関係・day を与え、学習の流れを組み立てる。
    materials: 教材の {title, kind}。kind は lecture/basic/other/test_info/
    past_exam。
    """
    system = (
        "あなたはカリキュラム設計者です。与えられた教材の本文を読み、"
        "「過去問から逆算」して学習マップに載せるノード構造を設計します。"
        "各ノードは学習のまとまり(単元・概念・演習)を表し、"
        "type は次のいずれかです:\n"
        "- discovery: 発見・概要（教材を読んで全体像をつかむ入口）\n"
        "- basic: 基礎概念（単一の概念・用語を理解確認）\n"
        "- practice: 演習（反復練習で「できる」化）\n"
        "- merge: 合流（複数の要素を組み合わせる総合問題）\n"
        "- gate: 診断チェック（前提ノードから混合問題を生成して弱点を検出）\n"
        "- boss: 総仕上げ（科目の最終確認・過去問演習）\n"
        "\n【生成手順（必須）】\n"
        "1. まず kind=past_exam の教材本文から、実際に出題されているテーマ・用語・"
        "出題形式を特定する。これが最優先でカバーすべき対象。\n"
        "2. 次に kind=lecture（レジュメ/講義資料）の本文を読み、過去問のテーマに"
        "対応する講義内容・用語を特定し、ノードの学習ポイントに反映する。\n"
        "3. テスト日から逆算して day を配分する。頻出テーマほど序盤に配置し、"
        "残りの日数で全体を網羅する。\n"
        "4. 過去問に出たテーマは必ずノードとして含める。講義のみで過去問に出ていない"
        "内容は「余力があれば」扱いにする。\n"
        "2日リズムを守り、各ノードに day(1〜テストまでの日数) を割り当てます。"
        "Day1 は「わかる」(discovery/basic)、Day2 は「できる」(practice/merge)。"
        "gate は basic/practice を 2 つ以上クリアした後に置き、boss は最後の過去問"
        "演習の日に置きます。from にはそのノードの前提となるノードidを入れます。"
        "ノード数は 6〜20 個程度にまとめます。"
        "過去問がある場合は最後に「過去問演習」の boss ノードを置きます。"
    )
    if study_method.strip():
        system += (
            "\n【学習者の学習法・方針（この方針に必ず従って設計すること）】\n"
            + study_method.strip()
        )
    system += (
        "\n出力は JSON のみ: {\"nodes\": [{\"id\": \"n1\", \"name\": \"ノード名\", "
        "\"type\": \"basic\", \"content\": \"学習ポイント(2〜3文)\", "
        "\"from\": [\"n0\"], \"day\": 1}], \"summary\": \"全体方針の短い説明\"}。"
        "id は n1,n2,... のような短いユニークな文字列にしてください。"
    )
    def fmt(m: dict) -> str:
        kind = m.get("kind", "")
        meta = f"{m.get('title','')} (kind={kind}"
        if m.get("year"):
            meta += f", 年度={m['year']}"
        meta += ")"
        content = (m.get("content") or "").strip()
        if not content:
            return f"- {meta} （本文なし）"
        return f"- {meta}\n  本文: {content}"
    mat_lines = "\n".join(fmt(m) for m in materials)
    user = (
        f"科目: {course_name}\nテストまで {test_days} 日。教材とOCR本文:\n{mat_lines or '(なし)'}\n\n"
        "過去問で問われているテーマを特定し、そこから逆算してこの科目の学習ノード構造を設計してください。"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def node_problems_messages(
    nodes: list[dict], exam_text: str = ""
) -> list[dict]:
    """設計済みノードの内部内容を深めるサブエージェント。

    各ノードについて、学習ポイントを「復習できる問題」に落とし込む。
    nodes: 第1段で生成された {id, name, type, content} の一覧。
    exam_text: 過去問のOCR本文。あれば出題形式・用語に合わせて問題を作る。
    """
    system = (
        "あなたはテスト作成のサブエージェントです。渡された各ノードの内容を深く理解し、"
        "そのノードを確実に理解できるようにするための復習問題を作成します。\n"
        "・各ノードに 2〜3 問（gate は 3〜4 問、boss は 3〜5 問）作成する。\n"
        "・短答式と選択式を混ぜる。選択式は options に 3〜4 個の選択肢を入れ、"
        "a には正解の選択肢の文字列そのものを入れる。\n"
        "・q は「〜とは何か」「〜はどうなるか」「なぜ〜か」のような明確な問い。\n"
        "・a は模範解答、why は「なぜそうなるのか」の解説(誤答処理に使う)。\n"
        "・間違えやすいポイント(ひっかけ)を含めるとよい。\n"
        "問題はすべて日本語で。"
        '出力は JSON のみ: {"problems": [{"node_id": "n1", "problems": ['
        '{"q": "...", "options": ["..."], "a": "...", "why": "..."}]}]}'
    )
    node_lines = "\n".join(
        f"- {n.get('id','')}: {n.get('name','')} (type={n.get('type','')}) "
        f"内容: {n.get('content','')}"
        for n in nodes
    )
    user = f"次のノードそれぞれに復習問題を作成してください:\n\n{node_lines}"
    if exam_text.strip():
        user += (
            "\n\n【過去問の出題傾向（可能なら同じ出題形式・用語で問題を作る）】\n"
            + exam_text.strip()[:2000]
        )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def plan_chat_messages(
    test_days: int,
    nodes: list[dict],
    history: list[dict],
    past_exams: list[dict] | None = None,
    study_method: str = "",
) -> list[dict]:
    """プランについて AI と話し合う相談チャット。

    history は過去のやり取り (role/content)。AI は会話に応じて日割りプランを
    提案・調整できる。プランを変更する場合のみ plan を返す。
    past_exams: 過去問一覧。テスト前に過去問演習の回を組み込める。
    study_method: 学習者の学習法・方針。非空なら必ず従う。
    """
    system = (
        "あなたは学習プランを一緒に考えるコーチです。プラン相談の相手として"
        "学習者と日本語で会話し、テストまでの日数・未クリアノード・ペース・復習の"
        "タイミングを考慮して日割りプランを提案・調整します。"
        "過去問・予想問題がある場合は、テスト前に過去問演習の回を組み込みます。"
        "過去問演習の回は nodes に [過去問演習: タイトル(年度)] の形式で含めます。"
        "要求が具体的になるまで質問してから提案するか、すぐに提案できます。"
    )
    if study_method.strip():
        system += (
            "\n【学習者の学習法・方針（この方針に必ず従うこと）】\n"
            + study_method.strip()
        )
    system += (
        '出力は JSON のみ: {"message": "学習者への返信(日本語)", '
        '"plan": [{"day": 1, "nodes": ["ノード名", ...], "note": "1日の狙い"}], '
        '"summary": "調整後の全体方針(プランを変えない場合は空文字)"} 。'
        "プランを変える場合のみ plan と summary を、会話のみなら message だけを返してください。"
    )
    node_lines = "\n".join(
        f"- {n.get('name','')} (type={n.get('type','')}, state={n.get('state','')})"
        for n in nodes
    )
    exam_lines = "\n".join(
        f"- {p.get('title','')} (年度 {p.get('year','')}, {p.get('exam_type','')})"
        for p in (past_exams or [])
    )
    messages = [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": (
                f"テストまで {test_days} 日。未クリアのノード:\n{node_lines or '(なし)'}\n\n"
                f"過去問:\n{exam_lines or '(なし)'}\n\n"
                "これからプランについて話し合います。最新の発言に返答してください。"
            ),
        },
    ]
    for h in history:
        messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
    return messages
