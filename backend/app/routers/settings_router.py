"""設定 API。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import llm, schemas
from ..config import settings as app_settings
from ..db import get_db

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=schemas.SettingsOut)
def get_settings(db: Session = Depends(get_db)):
    return schemas.SettingsOut(
        api_base_url=llm.get_setting(db, "api_base_url"),
        api_key_set=bool(llm.get_setting(db, "api_key")),
        vision_model=llm.get_setting(db, "vision_model"),
        text_model=llm.get_setting(db, "text_model"),
        new_per_day=llm.get_setting(db, "new_per_day"),
        desired_retention=llm.get_setting(db, "desired_retention"),
        context_char_budget=llm.get_setting(db, "context_char_budget"),
        llm_mock=app_settings.llm_mock,
    )


@router.put("", response_model=schemas.SettingsOut)
def update_settings(payload: schemas.SettingsIn, db: Session = Depends(get_db)):
    for key, value in payload.model_dump(exclude_none=True).items():
        # 空文字の api_key は「変更なし」とみなす
        if key == "api_key" and value == "":
            continue
        llm.set_setting(db, key, value)
    db.commit()
    return get_settings(db)


@router.post("/test")
def test_connection(db: Session = Depends(get_db)):
    try:
        models = llm.list_models(db)
        return {"ok": True, "models": models[:100], "count": len(models)}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"接続に失敗しました: {exc}")
