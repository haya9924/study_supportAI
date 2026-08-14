"""科目 API。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import schemas
from ..db import get_db
from ..models import Course, Material, Plan
from .plans_router import _ensure_plan_for_course

router = APIRouter(prefix="/api/courses", tags=["courses"])


def _to_out(course: Course, count: int) -> schemas.CourseOut:
    return schemas.CourseOut(
        id=course.id,
        name=course.name,
        created_at=course.created_at,
        material_count=count,
    )


@router.get("", response_model=list[schemas.CourseOut])
def list_courses(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Course, func.count(Material.id))
        .outerjoin(Material, Material.course_id == Course.id)
        .group_by(Course.id)
        .order_by(Course.name)
    ).all()
    return [_to_out(course, count) for course, count in rows]


@router.post("", response_model=schemas.CourseOut)
def create_course(payload: schemas.CourseIn, db: Session = Depends(get_db)):
    course = Course(name=payload.name.strip() or "無題の科目")
    db.add(course)
    db.commit()
    db.refresh(course)
    _ensure_plan_for_course(db, course)
    return _to_out(course, 0)


@router.put("/{course_id}", response_model=schemas.CourseOut)
def rename_course(
    course_id: int, payload: schemas.CourseIn, db: Session = Depends(get_db)
):
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(404, "科目が見つかりません")
    course.name = payload.name.strip() or course.name
    db.commit()
    plan = db.scalar(select(Plan).where(Plan.course_id == course_id))
    if plan is not None and plan.name != course.name:
        plan.name = course.name
        db.commit()
    db.refresh(course)
    count = (
        db.scalar(
            select(func.count(Material.id)).where(Material.course_id == course_id)
        )
        or 0
    )
    return _to_out(course, count)


@router.delete("/{course_id}")
def delete_course(course_id: int, db: Session = Depends(get_db)):
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(404, "科目が見つかりません")
    db.delete(course)
    db.commit()
    return {"ok": True}
