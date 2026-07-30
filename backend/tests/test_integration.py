"""モック LLM を使ったエンドツーエンド統合テスト。

アップロード → OCR → カード生成 → FSRS 復習 → クイズ → 予想問題 を一通り検証する。
"""
import io
import time

from PIL import Image


def _jpeg_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (800, 600), "white").save(buf, format="JPEG")
    return buf.getvalue()


def _upload_and_wait(client, course_id: int) -> int:
    files = {"files": ("note.jpg", _jpeg_bytes(), "image/jpeg")}
    data = {"course_id": str(course_id), "kind": "lecture"}
    res = client.post("/api/materials", files=files, data=data)
    assert res.status_code == 200, res.text
    mid = res.json()[0]["id"]
    # OCR 完了を待つ (BackgroundTasks は非同期のためポーリング)
    for _ in range(50):
        st = client.get(f"/api/materials/{mid}/status").json()
        if st["material_status"] in ("ready", "error"):
            break
        time.sleep(0.1)
    assert st["material_status"] == "ready", st
    return mid


def test_settings_roundtrip(client):
    res = client.get("/api/settings")
    assert res.status_code == 200
    assert res.json()["llm_mock"] is True
    # 接続テスト (モック)
    t = client.post("/api/settings/test")
    assert t.status_code == 200
    assert t.json()["ok"] is True


def test_full_flow(client):
    # 科目作成
    course = client.post("/api/courses", json={"name": "生物学"}).json()
    cid = course["id"]

    # 教材アップロード + OCR
    mid = _upload_and_wait(client, cid)
    detail = client.get(f"/api/materials/{mid}").json()
    assert detail["pages"][0]["ocr_text"]  # モック OCR テキストが入る

    # --- フラッシュカード ---
    deck = client.post("/api/decks", json={"name": "生物デッキ"}).json()
    did = deck["id"]
    drafts = client.post(
        "/api/generate/flashcards",
        json={"material_ids": [mid], "count": 5},
    ).json()
    assert len(drafts) >= 1
    client.post(f"/api/decks/{did}/cards/bulk", json={"cards": drafts})

    # 次のカードを取得 → 復習
    nxt = client.get(f"/api/decks/{did}/next").json()
    assert nxt["card"] is not None
    assert set(nxt["intervals"].keys()) == {"1", "2", "3", "4"}
    reviewed = client.post(
        f"/api/decks/cards/{nxt['card']['id']}/review", json={"rating": 3}
    ).json()
    # 復習後、レビューログが残る (ダッシュボードで確認)
    dash = client.get("/api/dashboard").json()
    assert dash["reviewed_today"] >= 1
    assert reviewed is not None

    # --- クイズ ---
    quiz = client.post(
        "/api/quizzes",
        json={"material_ids": [mid], "count": 3, "title": "小テスト"},
    ).json()
    qid = quiz["id"]
    assert len(quiz["questions"]) >= 1

    attempt = client.post(f"/api/quizzes/{qid}/attempt").json()
    aid = attempt["id"]
    # 各問に解答 (途中保存を確認)
    for q in quiz["questions"]:
        ans = "0" if q["type"] == "mcq" else (
            "true" if q["type"] == "tf" else "酸素"
        )
        r = client.post(
            f"/api/quizzes/attempt/{aid}/answer",
            json={"question_id": q["id"], "response": ans},
        )
        assert r.status_code == 200
        assert "correct" in r.json()

    # 途中再開: 同じ attempt が返る
    resumed = client.post(f"/api/quizzes/{qid}/attempt").json()
    assert resumed["id"] == aid
    assert len(resumed["answers"]) == len(quiz["questions"])

    finished = client.post(f"/api/quizzes/attempt/{aid}/finish").json()
    assert finished["status"] == "done"
    assert 0 <= finished["score"] <= 100

    # --- 予想問題 ---
    exam = client.post(
        "/api/exams",
        json={"material_ids": [mid], "title": "予想問題"},
    ).json()
    assert exam["content_md"]
    revised = client.post(
        f"/api/exams/{exam['id']}/revise", json={"instruction": "難しくして"}
    ).json()
    assert revised["content_md"]
    # 指示履歴が積み上がる
    user_msgs = [m for m in revised["messages"] if m["role"] == "user"]
    assert len(user_msgs) == 2


def test_course_folders_count_rename_move(client):
    # 科目フォルダ作成 → 直後は 0 件
    a = client.post("/api/courses", json={"name": "数学"}).json()
    b = client.post("/api/courses", json={"name": "物理"}).json()
    assert a["material_count"] == 0

    # 数学フォルダへアップロード → 件数が反映される
    mid = _upload_and_wait(client, a["id"])
    courses = {c["id"]: c for c in client.get("/api/courses").json()}
    assert courses[a["id"]]["material_count"] == 1
    assert courses[b["id"]]["material_count"] == 0

    # リネーム
    renamed = client.put(f"/api/courses/{a['id']}", json={"name": "解析学"}).json()
    assert renamed["name"] == "解析学"
    assert renamed["material_count"] == 1

    # 物理フォルダへ移動
    client.put(f"/api/materials/{mid}/move", json={"course_id": b["id"]})
    courses = {c["id"]: c for c in client.get("/api/courses").json()}
    assert courses[a["id"]]["material_count"] == 0
    assert courses[b["id"]]["material_count"] == 1

    # 未分類へ移動 → uncategorized フィルタで取得できる
    client.put(f"/api/materials/{mid}/move", json={"course_id": None})
    uncat = client.get("/api/materials?uncategorized=1").json()
    assert any(m["id"] == mid for m in uncat)
    assert client.get(f"/api/materials?course_id={b['id']}").json() == []


def test_new_per_day_limit(client):
    """1 日の新規カード上限が守られること。"""
    deck = client.post(
        "/api/decks", json={"name": "上限テスト", "new_per_day": 2}
    ).json()
    did = deck["id"]
    cards = [{"front": f"Q{i}", "back": f"A{i}"} for i in range(5)]
    client.post(f"/api/decks/{did}/cards/bulk", json={"cards": cards})

    stats = [d for d in client.get("/api/decks").json() if d["id"] == did][0]
    assert stats["new_count"] == 2  # 5 枚あっても上限 2


def test_undo_review(client):
    deck = client.post("/api/decks", json={"name": "取消テスト"}).json()
    did = deck["id"]
    client.post(f"/api/decks/{did}/cards", json={"front": "Q", "back": "A"})

    nxt = client.get(f"/api/decks/{did}/next").json()
    cid = nxt["card"]["id"]
    assert nxt["card"]["is_new"] is True and nxt["card"]["reps"] == 0

    # 回答するとカードが更新される
    client.post(f"/api/decks/cards/{cid}/review", json={"rating": 3})
    after = client.get(f"/api/decks/{did}/cards").json()[0]
    assert after["reps"] == 1 and after["is_new"] is False

    # 1つ戻る: 復習前の状態に完全復元され、そのカードが現在のカードとして返る
    undone = client.post(f"/api/decks/{did}/undo").json()
    assert undone["card"]["id"] == cid
    assert undone["card"]["reps"] == 0 and undone["card"]["is_new"] is True
    assert undone["new_remaining"] == 1  # 新規カードの1日枠も戻る

    # 履歴が無くなったので再度の取り消しは 400
    assert client.post(f"/api/decks/{did}/undo").status_code == 400


def test_delete_card(client):
    deck = client.post("/api/decks", json={"name": "削除テスト"}).json()
    did = deck["id"]
    c = client.post(f"/api/decks/{did}/cards", json={"front": "x", "back": "y"}).json()
    assert len(client.get(f"/api/decks/{did}/cards").json()) == 1
    client.delete(f"/api/decks/cards/{c['id']}")
    assert client.get(f"/api/decks/{did}/cards").json() == []


def test_deck_rename(client):
    deck = client.post("/api/decks", json={"name": "旧デッキ名"}).json()
    did = deck["id"]

    updated = client.put(f"/api/decks/{did}", json={"name": "新デッキ名"}).json()
    assert updated["name"] == "新デッキ名"

    # 一覧にも反映される
    decks = {d["id"]: d for d in client.get("/api/decks").json()}
    assert decks[did]["name"] == "新デッキ名"

    # 空白のみは無視して既存名を維持
    same = client.put(f"/api/decks/{did}", json={"name": "   "}).json()
    assert same["name"] == "新デッキ名"

    # 存在しないデッキは 404
    assert client.put("/api/decks/999999", json={"name": "x"}).status_code == 404


def test_exam_structured_and_followup(client):
    course = client.post("/api/courses", json={"name": "化学"}).json()
    mid = _upload_and_wait(client, course["id"])

    exam = client.post(
        "/api/exams", json={"material_ids": [mid], "title": "予想"}
    ).json()
    # 構造化された設問 (問題/解答/解説) が返る
    assert exam["questions"] and len(exam["questions"]) >= 1
    q0 = exam["questions"][0]
    assert q0["problem"] and q0["answer"] and q0["explanation"]
    assert q0["followups"] == []
    # 印刷用の content_md も維持
    assert exam["content_md"]

    # 追加質問 → その設問の followups に user/assistant が追記される
    updated = client.post(
        f"/api/exams/{exam['id']}/questions/0/ask", json={"question": "なぜですか？"}
    ).json()
    fu = updated["questions"][0]["followups"]
    assert len(fu) == 2
    assert fu[0]["role"] == "user" and fu[0]["content"] == "なぜですか？"
    assert fu[1]["role"] == "assistant" and fu[1]["content"]
    # 他の設問には影響しない
    assert updated["questions"][1]["followups"] == []

    # 範囲外の設問は 404
    assert (
        client.post(
            f"/api/exams/{exam['id']}/questions/99/ask", json={"question": "x"}
        ).status_code
        == 404
    )


def test_new_per_day_default_and_override(client):
    # デフォルト出題枚数を 3 に設定
    client.put("/api/settings", json={"new_per_day": "3"})
    try:
        # 新規デッキは new_per_day=0 (=デフォルトに従う)
        deck = client.post("/api/decks", json={"name": "追従デッキ"}).json()
        did = deck["id"]
        assert deck["new_per_day"] == 0
        client.post(
            f"/api/decks/{did}/cards/bulk",
            json={"cards": [{"front": f"Q{i}", "back": "A"} for i in range(5)]},
        )

        stats = client.get(f"/api/decks/{did}").json()
        assert stats["effective_new_per_day"] == 3
        assert stats["new_count"] == 3  # デフォルト3が適用される

        # 個別に 1 へ変更 → 個別値が優先
        client.put(f"/api/decks/{did}", json={"new_per_day": 1})
        stats = client.get(f"/api/decks/{did}").json()
        assert stats["new_per_day"] == 1
        assert stats["effective_new_per_day"] == 1
        assert stats["new_count"] == 1

        # 0 に戻すとデフォルトに従う
        client.put(f"/api/decks/{did}", json={"new_per_day": 0})
        stats = client.get(f"/api/decks/{did}").json()
        assert stats["effective_new_per_day"] == 3
        assert stats["new_count"] == 3
    finally:
        # 他テストへの影響を避けるためデフォルトを戻す
        client.put("/api/settings", json={"new_per_day": "20"})


def test_text_material_and_kind_aware_exam(client):
    course = client.post("/api/courses", json={"name": "統計学"}).json()
    cid = course["id"]

    # テスト情報(テキスト教材)を追加 → OCR不要で即 ready
    ti = client.post(
        "/api/materials/text",
        json={
            "course_id": cid,
            "title": "テスト範囲",
            "text": "大問5題・すべて記述式・証明問題を2題含む",
            "kind": "test_info",
        },
    ).json()
    assert ti["kind"] == "test_info"
    assert ti["status"] == "ready"
    detail = client.get(f"/api/materials/{ti['id']}").json()
    assert detail["pages"][0]["ocr_text"].startswith("大問5題")
    assert detail["pages"][0]["has_image"] is False

    # 過去問(テキスト)を追加
    pe = client.post(
        "/api/materials/text",
        json={
            "course_id": cid,
            "title": "2023過去問",
            "text": "問1 平均を求めよ / 問2 分散を求めよ",
            "kind": "past_exam",
        },
    ).json()

    # 両方を選んで予想問題生成が動く
    exam = client.post(
        "/api/exams",
        json={"material_ids": [ti["id"], pe["id"]], "title": "予想"},
    ).json()
    assert exam["questions"]

    # テスト情報のみの科目からフラッシュカードを作ろうとすると、
    # test_info は学習素材から除外されるため対象なしで 400
    only_ti_course = client.post("/api/courses", json={"name": "情報のみ"}).json()
    only_ti = client.post(
        "/api/materials/text",
        json={"course_id": only_ti_course["id"], "text": "形式メモ", "kind": "test_info"},
    ).json()
    r = client.post(
        "/api/generate/flashcards", json={"material_ids": [only_ti["id"]]}
    )
    assert r.status_code == 400

    # 空テキストは 400
    assert client.post("/api/materials/text", json={"text": "   "}).status_code == 400


def test_exam_prompt_includes_kind_instructions():
    from app import prompts

    msgs = prompts.exam_messages(
        [{"role": "user", "content": "作って"}],
        past_exam="過去問の本文サンプル",
        test_info="出題範囲メモ",
        reference="講義ノート",
        budget=12000,
    )
    system = msgs[0]["content"]
    assert "忠実に踏襲" in system  # 過去問の形式踏襲の指示
    user = msgs[1]["content"]
    # 種別ごとにラベル付けされ、本文も含まれる
    assert "過去問" in user and "過去問の本文サンプル" in user
    assert "テスト情報" in user and "出題範囲メモ" in user
