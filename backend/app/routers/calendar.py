from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


@router.get("/{the_date}", response_model=schemas.DailyActivitiesOut)
def get_daily_activities(the_date: date, db: Session = Depends(get_db)):
    """All tasks scheduled for a given date - this is what the calendar
    click-a-date panel calls."""
    occs = (
        db.query(models.TaskOccurrence)
        .options(joinedload(models.TaskOccurrence.task))
        .filter(models.TaskOccurrence.scheduled_date == the_date)
        .all()
    )
    return {"date": the_date, "occurrences": occs}


@router.get("/month/{year}/{month}")
def get_month_summary(year: int, month: int, db: Session = Depends(get_db)):
    """Lightweight per-day counts for painting the calendar grid
    (e.g. dots/badges showing how many tasks are due each day)."""
    rows = (
        db.query(models.TaskOccurrence.scheduled_date, models.TaskOccurrence.is_done)
        .filter(
            models.TaskOccurrence.scheduled_date >= date(year, month, 1),
            models.TaskOccurrence.scheduled_date < date(year + (month == 12), (month % 12) + 1, 1),
        )
        .all()
    )
    summary = {}
    for d, done in rows:
        key = d.isoformat()
        summary.setdefault(key, {"total": 0, "done": 0})
        summary[key]["total"] += 1
        summary[key]["done"] += int(done)
    return summary
