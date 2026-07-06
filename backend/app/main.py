"""FastAPI エントリポイント。API + フロントエンド静的配信。"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .db import init_db
from .routers import (
    courses_router,
    dashboard_router,
    decks_router,
    exams_router,
    generate_router,
    materials_router,
    quizzes_router,
    settings_router,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="study_supportAI", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(settings_router.router)
app.include_router(courses_router.router)
app.include_router(materials_router.router)
app.include_router(generate_router.router)
app.include_router(decks_router.router)
app.include_router(quizzes_router.router)
app.include_router(exams_router.router)
app.include_router(dashboard_router.router)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


# --- フロントエンド静的配信 (frontend/dist をビルド後に配置) ---
DIST_DIR = Path(__file__).resolve().parent.parent / "frontend_dist"

if DIST_DIR.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=DIST_DIR / "assets"),
        name="assets",
    )

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        # API 以外は index.html を返し、クライアントルーティングに委ねる
        candidate = DIST_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(DIST_DIR / "index.html")
