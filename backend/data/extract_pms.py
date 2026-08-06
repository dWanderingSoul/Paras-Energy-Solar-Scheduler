"""
Extract the PMS sheet from 17MW_Solar_Plant_Maintenance_Plan.xlsx into clean JSON.
Category and Task cells are merged/blank-filled downward in the source sheet,
so we forward-fill them here to reconstruct the true category/task per row.
"""
import openpyxl
import json

SRC = "/mnt/user-data/uploads/17MW_Solar_Plant_Maintenance_Plan.xlsx"
OUT = "/home/claude/solar-app/backend/data/pms_tasks.json"

FREQ_COLS = ["daily", "weekly", "monthly", "quarterly", "bi_annually", "annually", "need_basis"]

wb = openpyxl.load_workbook(SRC, data_only=True)
ws = wb["PMS"]

tasks = []
current_category = None
current_task = None
tid = 0

for row in ws.iter_rows(min_row=5, max_row=40, values_only=True):
    _, category, task, activity, *freqs = row
    if category:
        current_category = category
    if task:
        current_task = task
    if not activity:
        continue

    freq_flags = dict(zip(FREQ_COLS, [bool(f) for f in freqs]))
    # determine primary frequency (first True flag, in priority order)
    primary_freq = next((f for f in FREQ_COLS if freq_flags.get(f)), "need_basis")

    tid += 1
    tasks.append({
        "id": tid,
        "category": current_category,
        "task_name": current_task,
        "activity": activity.strip(),
        "frequency_flags": freq_flags,
        "primary_frequency": primary_freq,
    })

with open(OUT, "w") as f:
    json.dump(tasks, f, indent=2)

print(f"Extracted {len(tasks)} PMS activities -> {OUT}")
for t in tasks:
    print(f"  [{t['id']:2}] {t['category']:20} | {t['task_name']:30} | {t['primary_frequency']}")
