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


@router.get("/overview/monthly", response_model=list[schemas.MonthlyTrackerRow])
def monthly_overview(year: int = Query(...), month: int = Query(...), db: Session = Depends(get_db)):
    """Full Monthly Task Tracker table - every task, ToDo/Done %, workflow checkmarks.
    Mirrors the Excel 'Monthly Task Tracker' sheet exactly."""
    start = date(year, month, 1)
    next_month = start.replace(month=start.month % 12 + 1, year=start.year + (start.month == 12))
    end = next_month - timedelta(days=1)

    tasks = db.query(models.MaintenanceTask).order_by(models.MaintenanceTask.category).all()
    rows = []
    for t in tasks:
        occs = (
            db.query(models.TaskOccurrence)
            .filter(
                models.TaskOccurrence.task_id == t.id,
                models.TaskOccurrence.scheduled_date >= start,
                models.TaskOccurrence.scheduled_date <= end,
            )
            .all()
        )
        total = len(occs)
        done = sum(1 for o in occs if o.is_done)
        done_pct = round((done / total) * 100, 0) if total else 0
        rows.append(schemas.MonthlyTrackerRow(
            task_id=t.id, category=t.category, task_name=t.task_name,
            todo_percent=100 - done_pct, done_percent=done_pct,
            is_drafted=t.is_drafted, is_submitted=t.is_submitted,
            is_reviewed=t.is_reviewed, is_approval=t.is_approval, is_approved=t.is_approved,
        ))
    return rows


@router.get("/overview/weekly", response_model=schemas.WeeklyOverviewOut)
def weekly_overview(from_date: date = Query(...), db: Session = Depends(get_db)):
    """Weekly Progress Tracker donut + Task List grid, aggregated across ALL tasks
    for the Mon-Sun week containing from_date. Mirrors the Excel 'Weekly Progress
    Tracker' + 'Task List' side by side."""
    start = from_date - timedelta(days=from_date.weekday())
    end = start + timedelta(days=6)

    occs = (
        db.query(models.TaskOccurrence)
        .options(joinedload(models.TaskOccurrence.task))
        .filter(models.TaskOccurrence.scheduled_date >= start, models.TaskOccurrence.scheduled_date <= end)
        .all()
    )
    total = len(occs)
    completed = sum(1 for o in occs if o.is_done)

    grid = {}
    for o in occs:
        key = o.task_id
        if key not in grid:
            grid[key] = {
                "task_id": o.task_id, "category": o.task.category,
                "task_name": o.task.task_name, "days": {},
            }
        grid[key]["days"][o.scheduled_date.isoformat()] = o.is_done

    return schemas.WeeklyOverviewOut(
        week_start=start, week_end=end, total=total, completed=completed,
        missing=total - completed,
        progress_percent=round((completed / total) * 100, 1) if total else 0.0,
        task_grid=list(grid.values()),
    )


@router.patch("/task/{task_id}/workflow", response_model=schemas.TaskOut)
def toggle_workflow(task_id: int, update: schemas.WorkflowUpdate,
                     db: Session = Depends(get_db), _=Depends(require_editor)):
    """Toggle one of the Drafted/Submitted/Reviewed/Approval/Approved checkmarks
    for a task - manual, per-task, matching the Excel Monthly Task Tracker."""
    task = db.query(models.MaintenanceTask).get(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    field_map = {
        "drafted": "is_drafted", "submitted": "is_submitted", "reviewed": "is_reviewed",
        "approval": "is_approval", "approved": "is_approved",
    }
    attr = field_map.get(update.field)
    if not attr:
        raise HTTPException(400, f"Unknown field '{update.field}'")
    setattr(task, attr, update.value)
    db.commit()
    db.refresh(task)
    return task


@router.patch("/occurrence/{occurrence_id}")
def mark_done(occurrence_id: int, update: schemas.OccurrenceUpdate,
              db: Session = Depends(get_db), _=Depends(require_editor)):
    occ = db.query(models.TaskOccurrence).get(occurrence_id)
    if not occ:
        raise HTTPException(404, "Occurrence not found")
    occ.is_done = update.is_done
    db.commit()
    return {"ok": True, "id": occ.id, "is_done": occ.is_done}
