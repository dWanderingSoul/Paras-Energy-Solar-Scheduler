"""
Populates the database from the extracted PMS/roster JSON.

Scheduling rules (per what was agreed):
- Tasks with an explicit roster (PV Module Cleaning -> dry cleaning roster,
  Vegetation trimming -> trimming roster, Garden tasks -> garden roster)
  get occurrences on exactly the weekdays/details the roster specifies.
- Daily tasks -> every day of the year.
- Weekly tasks with no roster -> every Monday (adjust in the app's Settings
  screen if a different day is wanted).
- Monthly -> the 1st of each month.
- Quarterly -> the 1st of Jan/Apr/Jul/Oct.
- Bi-annually -> the 1st of Jan and Jul.
- Annually -> the 1st of Jan.
- Need-basis -> no occurrences generated (these are logged ad hoc, not scheduled).

Run with: python -m app.seed [year]
"""
import json
import sys
from datetime import date, timedelta
from pathlib import Path

from .database import SessionLocal, engine, Base
from .models import MaintenanceTask, TaskOccurrence

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

WEEKDAY_FULL = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
                "Friday": 4, "Saturday": 5, "Sunday": 6}
WEEKDAY_ABBR = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}


def dates_in_year(year: int):
    d = date(year, 1, 1)
    end = date(year, 12, 31)
    while d <= end:
        yield d
        d += timedelta(days=1)


def dates_for_weekday(year: int, weekday_index: int):
    return [d for d in dates_in_year(year) if d.weekday() == weekday_index]


def seed(year: int):
    # drop_all + create_all so schema changes (e.g. new columns) take effect -
    # this wipes all done/workflow status, which is fine pre-launch but NOT
    # once the team is relying on saved progress day to day.
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    pms_tasks = json.loads((DATA_DIR / "pms_tasks.json").read_text())
    rosters = json.loads((DATA_DIR / "rosters.json").read_text())

    task_rows = {}
    for t in pms_tasks:
        row = MaintenanceTask(
            category=t["category"],
            task_name=t["task_name"],
            activity=t["activity"],
            frequency=t["primary_frequency"],
        )
        db.add(row)
        db.flush()
        task_rows[t["id"]] = row

    def add_occurrence(task_row, d, detail=None):
        db.add(TaskOccurrence(task_id=task_row.id, scheduled_date=d, detail=detail))

    # --- roster-driven tasks override the generic frequency rule ---
    ROSTER_OVERRIDES = {
        ("PV Module", "Cleaning"): ("dry_cleaning_roster", WEEKDAY_FULL),
        ("PV Module", "Vegetation trimming"): ("vegetation_trimming_roster", WEEKDAY_FULL),
    }

    for t in pms_tasks:
        row = task_rows[t["id"]]
        key = (t["category"], t["task_name"])
        freq = t["primary_frequency"]

        if key in ROSTER_OVERRIDES:
            roster_key, wmap = ROSTER_OVERRIDES[key]
            for entry in rosters[roster_key]:
                wd = wmap.get(entry["weekday"])
                if wd is None:
                    continue
                detail_parts = [v for k, v in entry.items() if k != "weekday" and v]
                detail = "; ".join(str(x).strip() for x in detail_parts) or None
                for d in dates_for_weekday(year, wd):
                    add_occurrence(row, d, detail)
            continue

        if freq == "need_basis":
            continue
        elif freq == "daily":
            for d in dates_in_year(year):
                add_occurrence(row, d)
        elif freq == "weekly":
            for d in dates_for_weekday(year, 0):  # default Monday
                add_occurrence(row, d)
        elif freq == "monthly":
            for m in range(1, 13):
                add_occurrence(row, date(year, m, 1))
        elif freq == "quarterly":
            for m in (1, 4, 7, 10):
                add_occurrence(row, date(year, m, 1))
        elif freq == "bi_annually":
            for m in (1, 7):
                add_occurrence(row, date(year, m, 1))
        elif freq == "annually":
            add_occurrence(row, date(year, 1, 1))

    # --- Garden tasks (separate category, from Garden sheet roster) ---
    garden_task_cache = {}
    for entry in rosters["garden_roster"]:
        wd = WEEKDAY_ABBR.get(entry["weekday"])
        if wd is None:
            continue
        task_name = entry["task"]
        if task_name not in garden_task_cache:
            g_row = MaintenanceTask(
                category="Garden",
                task_name=task_name,
                activity=f"{task_name} ({entry['shift']} shift)",
                frequency="weekly",
            )
            db.add(g_row)
            db.flush()
            garden_task_cache[task_name] = g_row
        g_row = garden_task_cache[task_name]
        loc = None
        if entry.get("location_from") or entry.get("location_to"):
            loc = f"{entry.get('location_from') or ''} -> {entry.get('location_to') or ''}".strip(" ->")
        detail = f"{entry['shift']} shift {entry.get('time_from','')}-{entry.get('time_to','')}"
        if loc:
            detail += f" | {loc}"
        for d in dates_for_weekday(year, wd):
            add_occurrence(g_row, d, detail)

    db.commit()
    total_tasks = db.query(MaintenanceTask).count()
    total_occ = db.query(TaskOccurrence).count()
    print(f"Seeded {total_tasks} tasks and {total_occ} occurrences for {year}.")
    db.close()


if __name__ == "__main__":
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
    seed(year)
