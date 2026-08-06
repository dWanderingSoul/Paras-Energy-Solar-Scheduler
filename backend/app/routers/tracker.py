from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from .. import models, schemas
from ..database import get_db
from ..auth import require_editor

router = APIRouter(prefix="/api/tracker", tags=["tracker"])


@router.get("/tasks", response_model=list[schemas.TaskOut])
def list_tasks(db: Session = Depends(get_db)):
    return db.query(models.MaintenanceTask).order_by(models.MaintenanceTask.category).all()


def _summary(db: Session, task_id: int, start: date, end: date):
    task = db.query(models.MaintenanceTask).get(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    occs = (
        db.query(models.TaskOccurrence)
        .options(joinedload(models.TaskOccurrence.task))
        .filter(
            models.TaskOccurrence.task_id == task_id,
            models.TaskOccurrence.scheduled_date >= start,
            models.TaskOccurrence.scheduled_date <= end,
        )
        .order_by(models.TaskOccurrence.scheduled_date)
        .all()
    )
    total = len(occs)
    completed = sum(1 for o in occs if o.is_done)
    return schemas.TrackerSummaryOut(
        task_id=task.id,
        task_name=task.task_name,
        category=task.category,
        period_start=start,
        period_end=end,
        total=total,
        completed=completed,
        missing=total - completed,
        progress_percent=round((completed / total) * 100, 1) if total else 0.0,
        occurrences=occs,
    )


@router.get("/task/{task_id}/weekly", response_model=schemas.TrackerSummaryOut)
def weekly_progress(task_id: int, from_date: date = Query(..., description="Any date in the target week"),
                     db: Session = Depends(get_db)):
    """Weekly progress for a task, for the Mon-Sun week containing from_date."""
    start = from_date - timedelta(days=from_date.weekday())  # back up to Monday
    end = start + timedelta(days=6)
    return _summary(db, task_id, start, end)


@router.get("/task/{task_id}/monthly", response_model=schemas.TrackerSummaryOut)
def monthly_progress(task_id: int, from_date: date = Query(..., description="Any date in the target month"),
                      db: Session = Depends(get_db)):
    """Monthly progress for a task, for the calendar month containing from_date."""
    start = from_date.replace(day=1)
    next_month = start.replace(month=start.month % 12 + 1, year=start.year + (start.month == 12))
    end = next_month - timedelta(days=1)
    return _summary(db, task_id, start, end)


@router.patch("/occurrence/{occurrence_id}")
def mark_done(occurrence_id: int, update: schemas.OccurrenceUpdate,
              db: Session = Depends(get_db), _=Depends(require_editor)):
    occ = db.query(models.TaskOccurrence).get(occurrence_id)
    if not occ:
        raise HTTPException(404, "Occurrence not found")
    occ.is_done = update.is_done
    db.commit()
    return {"ok": True, "id": occ.id, "is_done": occ.is_done}
