"""pytest 共通フィクスチャ。

一時 DATA_DIR + モック LLM で FastAPI アプリを起動する。環境変数は app を
import する前に設定する必要があるため、モジュール最上部で行う。
"""
import os
import tempfile

# --- app を import する前に設定 ---
_TMP = tempfile.mkdtemp(prefix="study_test_")
os.environ["DATA_DIR"] = _TMP
os.environ["LLM_MOCK"] = "1"

import pytest
from fastapi.testclient import TestClient

from app.db import init_db
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def _init():
    init_db()


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c
