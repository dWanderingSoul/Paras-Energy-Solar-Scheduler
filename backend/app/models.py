from sqlalchemy import Column, Integer, String, Date, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from .database import Base


class MaintenanceTask(Base):
    """One row per activity from the PMS sheet (36 total)."""
    __tablename__ = "maintenance_tasks"

    id = Column(Integer, primary_key=True)
    category = Column(String, nullable=False)       # e.g. "PV Module"
    task_name = Column(String, nullable=False)       # e.g. "Cleaning"
    activity = Column(Text, nullable=False)          # full description
    frequency = Column(String, nullable=False)       # daily/weekly/monthly/...

    occurrences = relationship("TaskOccurrence", back_populates="task")


class TaskOccurrence(Base):
    """One row per task per scheduled calendar date. This is what the
    calendar view and tracker view both query against."""
    __tablename__ = "task_occurrences"

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("maintenance_tasks.id"), nullable=False)
    scheduled_date = Column(Date, nullable=False, index=True)
    detail = Column(String, nullable=True)   # e.g. "LT-P1, Inv: 1-6" for roster-based tasks
    is_done = Column(Boolean, default=False, nullable=False)

    task = relationship("MaintenanceTask", back_populates="occurrences")
