from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from .routers import calendar, tracker

app = FastAPI(title="17MW Solar Plant O&M Scheduler")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # single-repo/single-host deploy, so this is generous on purpose
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(calendar.router)
app.include_router(tracker.router)

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"

app.mount("/static", StaticFiles(directory=FRONTEND_DIR / "static"), name="static")


@app.get("/")
def serve_index():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/tracker")
def serve_tracker_page():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok"}
