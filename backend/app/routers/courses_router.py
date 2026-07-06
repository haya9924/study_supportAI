"""科目 API。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import schemas
from ..db import get_db
from ..models import Course

router = APIRouter(prefix="/api/courses", tags=["courses"])


@router.get("", response_model=list[schemas.CourseOut])
def list_courses(db: Session = Depends(get_db)):
    return db.scalars(select(Course).order_by(Course.name)).all()


@router.post("", response_model=schemas.CourseOut)
def create_course(payload: schemas.CourseIn, db: Session = Depends(get_db)):
    course = Course(name=payload.name.strip() or "無題の科目")
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@router.delete("/{course_id}")
def delete_course(course_id: int, db: Session = Depends(get_db)):
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(404, "科目が見つかりません")
    db.delete(course)
    db.commit()
    return {"ok": True}
