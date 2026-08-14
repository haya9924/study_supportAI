"""Pydantic スキーマ (API 入出力)。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- settings ---
class SettingsIn(BaseModel):
    api_base_url: str | None = None
    api_key: str | None = None
    vision_model: str | None = None
    text_model: str | None = None
    new_per_day: str | None = None
    desired_retention: str | None = None
    context_char_budget: str | None = None
    test_date: str | None = None
    test_goal: str | None = None
    study_method: str | None = None
    materials_dir: str | None = None


class SettingsOut(BaseModel):
    api_base_url: str
    api_key_set: bool
    vision_model: str
    text_model: str
    new_per_day: str
    desired_retention: str
    context_char_budget: str
    test_date: str
    test_goal: str
    study_method: str
    materials_dir: str
    llm_mock: bool


# --- courses ---
class CourseIn(BaseModel):
    name: str


class CourseOut(ORMModel):
    id: int
    name: str
    created_at: datetime
    material_count: int = 0


# --- plans ---
class PlanOut(ORMModel):
    id: int
    course_id: int | None
    name: str
    status: str
    test_days: int = 14
    material_count: int = 0
    built_count: int = 0
    days: list[dict] = []
    nodes: list[dict] = []
    problems: dict = {}
    summary: str = ""


class PlanBuildIn(BaseModel):
    test_days: int = 14


# --- materials ---
class PageOut(ORMModel):
    id: int
    page_no: int
    ocr_text: str
    status: str
    error: str
    has_image: bool = False


class MaterialOut(ORMModel):
    id: int
    course_id: int | None
    kind: str
    title: str
    original_filename: str
    year: str = ""
    exam_type: str = ""
    status: str
    error: str
    created_at: datetime


class MaterialDetail(MaterialOut):
    pages: list[PageOut]


class PageTextIn(BaseModel):
    ocr_text: str


class MaterialMetaIn(BaseModel):
    kind: str = "lecture"
    title: str | None = None
    year: str = ""
    exam_type: str = ""


class MaterialTextIn(BaseModel):
    course_id: int | None = None
    title: str = ""
    text: str
    kind: str = "test_info"


class MaterialMoveIn(BaseModel):
    course_id: int | None = None


# --- generation ---
class GenerateIn(BaseModel):
    course_id: int | None = None
    material_ids: list[int] = []
    instruction: str = ""
    count: int = 15
    title: str | None = None


# --- decks / cards ---
class DeckIn(BaseModel):
    name: str
    course_id: int | None = None
    new_per_day: int = 0  # 0 = デフォルトに従う


class DeckUpdateIn(BaseModel):
    name: str | None = None
    new_per_day: int | None = None  # 0 = デフォルトに従う


class DeckOut(ORMModel):
    id: int
    name: str
    course_id: int | None
    new_per_day: int
    created_at: datetime


class DeckStats(DeckOut):
    total: int
    due_count: int
    new_count: int
    effective_new_per_day: int  # 実際に適用される1日の出題枚数


class CardIn(BaseModel):
    front: str
    back: str


class CardOut(ORMModel):
    id: int
    deck_id: int
    front: str
    back: str
    due: datetime
    reps: int
    is_new: bool
    suspended: bool


class CardDraft(BaseModel):
    front: str
    back: str


class AddCardsIn(BaseModel):
    cards: list[CardDraft]


class ReviewIn(BaseModel):
    rating: int  # 1-4


class ReviewCardOut(BaseModel):
    card: CardOut | None
    intervals: dict[int, str] | None
    remaining: int
    new_remaining: int


# --- quiz ---
class QuizQuestionOut(ORMModel):
    id: int
    order_no: int
    type: str
    question: str
    choices: list
    # answer/explanation は結果確定まで隠す用途で別途返す


class QuizOut(ORMModel):
    id: int
    course_id: int | None
    title: str
    created_at: datetime


class QuizDetail(QuizOut):
    questions: list[QuizQuestionOut]


class AttemptAnswerIn(BaseModel):
    question_id: int
    response: str


class AttemptOut(BaseModel):
    id: int
    quiz_id: int
    status: str
    answers: dict
    score: float
