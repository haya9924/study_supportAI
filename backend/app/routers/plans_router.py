"""プラン API。

科目(フォルダ)ごとの学習プランを管理する。科目の作成/スキャンで
自動的に「中身なし(empty)」のプランが作られ、教材から具体的な
日割りプラン(content)を構築できる。
"""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import llm, prompts, schemas
from ..config import settings
from ..db import get_db
from ..models import Course, Material, Plan

router = APIRouter(prefix="/api/plans", tags=["plans"])


def _ensure_plan_for_course(db: Session, course: Course) -> Plan:
    plan = db.scalar(select(Plan).where(Plan.course_id == course.id))
    if plan is None:
        plan = Plan(course_id=course.id, name=course.name, status="empty")
        db.add(plan)
        db.commit()
        db.refresh(plan)
    return plan


def _schedule_from_materials(test_days: int, materials: list[Material]) -> dict:
    """教材一覧から決定的な日割りプランを組み立てる (モック時に days 表示用)。"""
    nodes = _nodes_from_materials(materials, test_days)
    return {
        "days": _days_from_nodes(nodes, test_days),
        "nodes": nodes,
        "problems": _extract_problems({}, nodes),
        "summary": f"{len(nodes)}個のノードに分解しました。",
    }


_VALID_TYPES = ("discovery", "basic", "practice", "merge", "gate", "boss")


def _sanitize_node(x: dict, idx: int) -> dict | None:
    nid = str(x.get("id") or f"n{idx}")
    ntype = str(x.get("type") or "basic")
    if ntype not in _VALID_TYPES:
        ntype = "basic"
    try:
        day = int(x.get("day") or 1)
    except (TypeError, ValueError):
        day = 1
    froms = []
    for f in x.get("from") or []:
        s = str(f)
        if s:
            froms.append(s)
    return {
        "id": nid,
        "name": str(x.get("name") or f"ノード{idx}"),
        "type": ntype,
        "content": str(x.get("content") or ""),
        "from": froms,
        "day": max(1, day),
    }


def _nodes_from_materials(materials: list[Material], test_days: int) -> list[dict]:
    """教材一覧から決定的なノード構造を組み立てる (LLM モック/失敗時の代替)。"""
    nodes: list[dict] = []
    ni = 0
    for m in materials:
        if m.kind == "past_exam":
            nodes.append(
                {
                    "id": f"n{ni}",
                    "name": f"過去問演習: {m.title}",
                    "type": "boss",
                    "content": "過去問を本番形式で時間を測って解き、間違えたポイントを補強する。",
                    "from": [nodes[-1]["id"]] if nodes else [],
                    "day": test_days,
                }
            )
            ni += 1
            continue
        base = f"n{ni}"
        nodes.append(
            {
                "id": base,
                "name": f"{m.title}の概要",
                "type": "discovery",
                "content": "教材を読んで全体像をつかむ（インプットは最小限）。",
                "from": [nodes[-1]["id"]] if nodes else [],
                "day": 1 + (ni // 2),
            }
        )
        ni += 1
        nodes.append(
            {
                "id": f"n{ni}",
                "name": f"{m.title}の理解チェック",
                "type": "basic",
                "content": "用語と仕組みを自分の言葉で説明できるか確認する。",
                "from": [base],
                "day": 1 + (ni // 2),
            }
        )
        ni += 1
        nodes.append(
            {
                "id": f"n{ni}",
                "name": f"{m.title}の演習",
                "type": "practice",
                "content": "例題・問題を解いて「できる」化する。間違いはなぜかを言語化。",
                "from": [f"n{ni - 1}"],
                "day": min(test_days, 1 + (ni // 2)),
            }
        )
        ni += 1
    if not nodes:
        nodes.append(
            {
                "id": "n0",
                "name": "教材を追加してから組み立ててください",
                "type": "discovery",
                "content": "教材フォルダに PDF を追加してスキャンしてください。",
                "from": [],
                "day": 1,
            }
        )
    return nodes


def _default_problems(n: dict) -> list[dict]:
    return [
        {
            "q": f"「{n['name']}」の要点を自分の言葉で説明できるか",
            "options": [],
            "a": "要点（定義・仕組み・例）を口頭で説明できる",
            "why": "説明できる＝理解できている。詰まる箇所を書き出して補強する。",
        },
        {
            "q": "このノードで一番重要なキーワードは何か",
            "options": [],
            "a": "ノード内の最重要用語を1つ挙げて、その定義を言える",
            "why": "最重要キーワードを押さえると全体の理解がまとまる。",
        },
    ]


def _extract_problems(pdata: dict, nodes: list[dict]) -> dict:
    problems: dict = {}
    for entry in pdata.get("problems") or []:
        if not isinstance(entry, dict):
            continue
        nid = str(entry.get("node_id") or "")
        plist = entry.get("problems") or []
        cleaned = []
        for p in plist:
            if not isinstance(p, dict) or not p.get("q"):
                continue
            opts = [
                str(o)
                for o in (p.get("options") or [])
                if isinstance(o, (str, int, float))
            ]
            cleaned.append(
                {
                    "q": str(p.get("q", "")),
                    "options": opts,
                    "a": str(p.get("a", "")),
                    "why": str(p.get("why", "")),
                }
            )
        if nid and cleaned:
            problems[nid] = cleaned
    for n in nodes:
        if n["id"] not in problems or not problems[n["id"]]:
            problems[n["id"]] = _default_problems(n)
    return problems


def _days_from_nodes(nodes: list[dict], test_days: int) -> list[dict]:
    by_day: dict[int, list[str]] = {}
    for n in nodes:
        d = max(1, min(int(n.get("day") or 1), test_days))
        by_day.setdefault(d, []).append(n.get("name", ""))
    return [
        {
            "day": d,
            "nodes": by_day[d],
            "note": "この日は「" + "、".join(by_day[d]) + "」を学習します。",
        }
        for d in sorted(by_day)
    ]


def _to_out(plan: Plan, count: int) -> schemas.PlanOut:
    content = plan.content or {}
    days = content.get("days") or []
    nodes = content.get("nodes") or []
    return schemas.PlanOut(
        id=plan.id,
        course_id=plan.course_id,
        name=plan.name,
        status=plan.status,
        test_days=plan.test_days,
        material_count=count,
        built_count=len(nodes),
        days=days,
        nodes=nodes,
        problems=content.get("problems") or {},
        summary=str(content.get("summary", "")),
    )


@router.get("", response_model=list[schemas.PlanOut])
def list_plans(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Plan, func.count(Material.id))
        .outerjoin(Course, Course.id == Plan.course_id)
        .outerjoin(Material, Material.course_id == Course.id)
        .group_by(Plan.id)
        .order_by(Plan.name)
    ).all()
    return [_to_out(plan, count) for plan, count in rows]


def _material_text(m: Material, cap: int) -> str:
    """教材のOCR本文を1行に圧縮して最大 cap 文字返す（本文が無ければ空）。"""
    text = " ".join(p.ocr_text for p in m.pages if (p.ocr_text or "").strip())
    text = re.sub(r"\s+", " ", text).strip()
    return text[:cap]


@router.post("/{plan_id}/build", response_model=schemas.PlanOut)
def build_plan(
    plan_id: int, payload: schemas.PlanBuildIn, db: Session = Depends(get_db)
):
    """テスト日数と科目の教材から、日割りの具体的なプランを構築して保存する。

    過去問(past_exam)の本文から出題テーマを特定し、テスト日から逆算して
    レジュメ(lecture)の内容を対応付けて、学習マップのノード構造を生成する。
    """
    plan = db.get(Plan, plan_id)
    if plan is None:
        raise HTTPException(404, "プランが見つかりません")

    days = max(1, min(90, payload.test_days or plan.test_days or 14))
    materials = (
        db.query(Material).filter(Material.course_id == plan.course_id).all()
        if plan.course_id
        else []
    )

    content: dict
    if settings.llm_mock:
        nodes = _nodes_from_materials(materials, days)
        problems = _extract_problems({}, nodes)
        content = {
            "nodes": nodes,
            "problems": problems,
            "days": _days_from_nodes(nodes, days),
            "summary": f"{len(nodes)}個のノードに分解しました。",
        }
    else:
        budget = int(llm.get_setting(db, "context_char_budget") or 12000)
        caps = {
            "past_exam": int(budget * 0.4),
            "lecture": int(budget * 0.35),
            "test_info": int(budget * 0.2),
            "other": int(budget * 0.1),
        }
        mat_dicts = [
            {
                "title": m.title,
                "kind": m.kind,
                "year": m.year or "",
                "content": _material_text(m, caps.get(m.kind, int(budget * 0.15))),
            }
            for m in materials
        ]
        study_method = llm.get_setting(db, "study_method")
        # 構造化された長い JSON を生成するため、高速なモデル(登録済み)を使う。
        # ユーザーが設定画面の「視覚モデル」に登録した gemini-2.5-flash 等が該当。
        gen_model = llm.get_setting(db, "vision_model") or None
        nodes: list[dict] = []
        summary = ""
        # 第1段: 学習マップのノード構造を設計する（カリキュラム設計）
        try:
            data = llm.chat_json(
                db,
                prompts.plan_nodes_messages(days, plan.name, mat_dicts, study_method),
                temperature=0.4,
                model=gen_model,
            )
            raw = data.get("nodes") or []
            nodes = [
                n
                for i, x in enumerate(raw)
                if (n := _sanitize_node(x, i)) is not None
            ]
            summary = str(data.get("summary", ""))
        except Exception:  # noqa: BLE001
            nodes = _nodes_from_materials(materials, days)
        # 第2段: サブエージェントでノード内部（復習問題）を生成する
        problems: dict = {}
        if nodes:
            exam_text = "\n".join(
                m.get("content", "") for m in mat_dicts if m.get("kind") == "past_exam"
            )
            try:
                pdata = llm.chat_json(
                    db,
                    prompts.node_problems_messages(nodes, exam_text),
                    temperature=0.3,
                    model=gen_model,
                )
                problems = _extract_problems(pdata if isinstance(pdata, dict) else {}, nodes)
            except Exception:  # noqa: BLE001
                problems = {}
            problems = _extract_problems({}, nodes) if not problems else problems
        content = {
            "nodes": nodes,
            "problems": problems,
            "days": _days_from_nodes(nodes, days),
            "summary": summary,
        }

    plan.test_days = days
    plan.content = content
    plan.status = "draft"
    db.commit()
    db.refresh(plan)
    count = (
        db.scalar(
            select(func.count(Material.id)).where(Material.course_id == plan.course_id)
        )
        if plan.course_id
        else 0
    ) or 0
    return _to_out(plan, count)


@router.put("/{plan_id}/test_days")
def set_test_days(
    plan_id: int, payload: schemas.PlanBuildIn, db: Session = Depends(get_db)
):
    plan = db.get(Plan, plan_id)
    if plan is None:
        raise HTTPException(404, "プランが見つかりません")
    plan.test_days = max(1, min(90, payload.test_days or 14))
    db.commit()
    return {"ok": True}
