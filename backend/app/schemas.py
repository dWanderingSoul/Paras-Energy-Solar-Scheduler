from pydantic import BaseModel
from datetime import date as date_type
from typing import Optional


class TaskOut(BaseModel):
    id: int
    category: str
    task_name: str
    activity: str
    frequency: str
    is_drafted: bool
    is_submitted: bool
    is_reviewed: bool
    is_approval: bool
    is_approved: bool

    class Config:
        from_attributes = True


class WorkflowUpdate(BaseModel):
    field: str  # one of: drafted, submitted, reviewed, approval, approved
    value: bool


class MonthlyTrackerRow(BaseModel):
    task_id: int
    category: str
    task_name: str
    todo_percent: float
    done_percent: float
    is_drafted: bool
    is_submitted: bool
    is_reviewed: bool
    is_approval: bool
    is_approved: bool


class WeeklyOverviewOut(BaseModel):
    week_start: date_type
    week_end: date_type
    total: int
    completed: int
    missing: int
    progress_percent: float
    task_grid: list[dict]  # [{task_id, category, task_name, days: {date: bool}}]


class OccurrenceOut(BaseModel):
    id: int
    task_id: int
    scheduled_date: date_type
    detail: Optional[str] = None
    is_done: bool
    task: TaskOut

    class Config:
        from_attributes = True


class OccurrenceUpdate(BaseModel):
    is_done: bool


class DailyActivitiesOut(BaseModel):
    date: date_type
    occurrences: list[OccurrenceOut]


class TrackerSummaryOut(BaseModel):
    task_id: int
    task_name: str
    category: str
    period_start: date_type
    period_end: date_type
    total: int
    completed: int
    missing: int
    progress_percent: float
    occurrences: list[OccurrenceOut]
