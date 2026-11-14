"""One background thread runs queued jobs in order, so only one render uses the GPU at a time."""

from __future__ import annotations

import threading
import time
import traceback
from datetime import UTC, datetime, timedelta

from . import db
from .pipeline import Pipeline

# kind -> (stage while running, stage on success, stage to fall back to on failure)
STAGES = {
    "pick": ("picking", "picks_ready", "found"),
    "render": ("rendering", "ready", "picks_ready"),
    "cleanup": ("cleaning", "done", "ready"),
}
SCAN_EVERY = timedelta(hours=24)


def start_job(kind: str, event_id: int | None = None) -> int:
    """Queue a job and move the event to its in-progress stage right away, so the UI updates."""
    prev = None
    if event_id is not None:
        ev = db.get_event(event_id)
        prev = ev["stage"] if ev and ev["stage"] not in db.ACTIVE_STAGES else None
    job_id = db.enqueue(kind, event_id, prev)
    if event_id is not None and kind in STAGES:
        db.set_stage(event_id, STAGES[kind][0])
    return job_id


class Worker(threading.Thread):
    def __init__(self, pipeline: Pipeline):
        super().__init__(daemon=True, name="highlights-worker")
        self.pipeline = pipeline
        self.stop_event = threading.Event()

    def run(self) -> None:
        db.requeue_interrupted_jobs()
        while not self.stop_event.is_set():
            self._maybe_schedule_scan()
            job = db.claim_next_job()
            if job is None:
                self.stop_event.wait(2)
                continue
            self._run(job)

    def _maybe_schedule_scan(self) -> None:
        last = db.get_meta("last_scan_at")
        due = last is None or datetime.now(UTC) - datetime.fromisoformat(last) > SCAN_EVERY
        if due and not db.active_job(None):
            db.enqueue("scan")

    def _run(self, job) -> None:
        kind, event_id, job_id = job["kind"], job["event_id"], job["id"]
        last_write = [0.0]

        def progress(fraction: float, message: str) -> None:
            if time.monotonic() - last_write[0] > 0.5 or fraction >= 1:
                db.update_job(job_id, progress=round(fraction, 3), message=message)
                last_write[0] = time.monotonic()

        try:
            if kind == "scan":
                self.pipeline.scan(progress)
            else:
                running, done, _ = STAGES[kind]
                db.set_stage(event_id, running)
                getattr(self.pipeline, kind)(event_id, progress)
                db.set_stage(event_id, done)
            db.finish_job(job_id)
        except Exception as e:  # noqa: BLE001 - every failure is reported to the UI
            message = str(e) or e.__class__.__name__
            traceback.print_exc()
            db.finish_job(job_id, error=message)
            if event_id is not None and kind in STAGES:
                db.set_stage(event_id, job["prev_stage"] or STAGES[kind][2], error=message)
            db.log(f"{kind.capitalize()} failed: {message}", event_id)
