from pydantic import BaseModel
from datetime import date as date_type
from typing import Optional


class TaskOut(BaseModel):
    id: int
    category: str
    task_name: str
    activity: str
    frequency: str

    class Config:
        from_attributes = True


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
