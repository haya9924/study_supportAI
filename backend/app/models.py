"""SQLAlchemy ORM モデル。"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Boolean,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")


class Course(Base):
    __tablename__ = "courses"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    materials: Mapped[list["Material"]] = relationship(
        back_populates="course", cascade="all, delete-orphan"
    )


class Material(Base):
    __tablename__ = "materials"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int | None] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(String, default="lecture")  # lecture/past_exam/other
    title: Mapped[str] = mapped_column(String, default="")
    original_filename: Mapped[str] = mapped_column(String, default="")
    stored_path: Mapped[str] = mapped_column(String, default="")
    mime: Mapped[str] = mapped_column(String, default="")
    status: Mapped[str] = mapped_column(String, default="uploaded")  # uploaded/processing/ready/error
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    course: Mapped[Course | None] = relationship(back_populates="materials")
    pages: Mapped[list["MaterialPage"]] = relationship(
        back_populates="material",
        cascade="all, delete-orphan",
        order_by="MaterialPage.page_no",
    )


class MaterialPage(Base):
    __tablename__ = "material_pages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    material_id: Mapped[int] = mapped_column(
        ForeignKey("materials.id", ondelete="CASCADE")
    )
    page_no: Mapped[int] = mapped_column(Integer, nullable=False)
    image_path: Mapped[str] = mapped_column(String, default="")
    ocr_text: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String, default="pending")  # pending/processing/done/error
    error: Mapped[str] = mapped_column(Text, default="")

    material: Mapped[Material] = relationship(back_populates="pages")


class ExamDoc(Base):
    __tablename__ = "exam_docs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int | None] = mapped_column(
        ForeignKey("courses.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String, default="")
    content_md: Mapped[str] = mapped_column(Text, default="")
    messages: Mapped[list] = mapped_column(JSON, default=list)  # 生成/改訂の履歴
    source_material_ids: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Quiz(Base):
    __tablename__ = "quizzes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int | None] = mapped_column(
        ForeignKey("courses.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String, default="")
    source_material_ids: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    questions: Mapped[list["QuizQuestion"]] = relationship(
        back_populates="quiz",
        cascade="all, delete-orphan",
        order_by="QuizQuestion.order_no",
    )
    attempts: Mapped[list["QuizAttempt"]] = relationship(
        back_populates="quiz", cascade="all, delete-orphan"
    )


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quiz_id: Mapped[int] = mapped_column(
        ForeignKey("quizzes.id", ondelete="CASCADE")
    )
    order_no: Mapped[int] = mapped_column(Integer, default=0)
    type: Mapped[str] = mapped_column(String, default="mcq")  # mcq/tf/short
    question: Mapped[str] = mapped_column(Text, default="")
    choices: Mapped[list] = mapped_column(JSON, default=list)  # mcq のみ
    answer: Mapped[str] = mapped_column(Text, default="")  # 正解 (mcq は index, tf は "true"/"false", short は文章)
    explanation: Mapped[str] = mapped_column(Text, default="")

    quiz: Mapped[Quiz] = relationship(back_populates="questions")


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quiz_id: Mapped[int] = mapped_column(
        ForeignKey("quizzes.id", ondelete="CASCADE")
    )
    status: Mapped[str] = mapped_column(String, default="in_progress")  # in_progress/done
    # {question_id: {"response": str, "correct": bool|None, "feedback": str}}
    answers: Mapped[dict] = mapped_column(JSON, default=dict)
    score: Mapped[float] = mapped_column(default=0.0)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    quiz: Mapped[Quiz] = relationship(back_populates="attempts")


class Deck(Base):
    __tablename__ = "decks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    course_id: Mapped[int | None] = mapped_column(
        ForeignKey("courses.id", ondelete="SET NULL")
    )
    new_per_day: Mapped[int] = mapped_column(Integer, default=20)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    cards: Mapped[list["Card"]] = relationship(
        back_populates="deck", cascade="all, delete-orphan"
    )


class Card(Base):
    __tablename__ = "cards"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deck_id: Mapped[int] = mapped_column(ForeignKey("decks.id", ondelete="CASCADE"))
    front: Mapped[str] = mapped_column(Text, default="")
    back: Mapped[str] = mapped_column(Text, default="")
    due: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    # FSRS カード状態 (シリアライズ済み dict)
    fsrs_state: Mapped[dict] = mapped_column(JSON, default=dict)
    reps: Mapped[int] = mapped_column(Integer, default=0)
    is_new: Mapped[bool] = mapped_column(Boolean, default=True)
    suspended: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    deck: Mapped[Deck] = relationship(back_populates="cards")


Index("ix_cards_deck_due", Card.deck_id, Card.due)


class ReviewLog(Base):
    __tablename__ = "review_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id", ondelete="CASCADE"))
    deck_id: Mapped[int] = mapped_column(Integer, index=True)
    rating: Mapped[int] = mapped_column(Integer)  # 1=Again 2=Hard 3=Good 4=Easy
    was_new: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(String)  # ocr など
    target_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String, default="running")  # running/done/error
    progress: Mapped[float] = mapped_column(default=0.0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    done: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
