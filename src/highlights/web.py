"""The phone PWA: follow each highlight through the pipeline and press the buttons that move it."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import db
from .config import Settings
from .pipeline import Pipeline
from .worker import start_job

HERE = Path(__file__).parent
STEPS = [("found", "Found"), ("picks_ready", "Picks"), ("rendering", "Render"),
         ("ready", "Watch"), ("done", "Clean up")]
STEP_OF = {"found": 0, "picking": 0, "picks_ready": 1, "rendering": 2, "ready": 3,
           "cleaning": 4, "done": 4, "dismissed": 0}
STAGE_LABEL = {
    "found": "Found", "picking": "Picking moments", "picks_ready": "Review picks",
    "rendering": "Rendering", "ready": "Ready to watch", "cleaning": "Cleaning up",
    "done": "Done", "dismissed": "Skipped",
}


def gb(n: float | None) -> str:
    n = n or 0
    if n >= 1e9:
        return f"{n / 1e9:.1f} GB"
    if n >= 1e6:
        return f"{n / 1e6:.0f} MB"
    return f"{n / 1e3:.0f} KB" if n else "0 MB"


def minutes(seconds: float | None) -> str:
    s = int(round(seconds or 0))
    if s < 60:
        return f"{s} sec"
    m, s = divmod(s, 60)
    if m < 60:
        return f"{m}:{s:02d}"
    h, m = divmod(m, 60)
    return f"{h} hr {m} min"


def span(seconds: float | None) -> str:
    """Long stretches in words: '38 min', '2 hr 5 min'."""
    m = int(round((seconds or 0) / 60))
    if m < 1:
        return f"{int(round(seconds or 0))} sec"
    if m < 60:
        return f"{m} min"
    h, m = divmod(m, 60)
    return f"{h} hr {m} min" if m else f"{h} hr"


def ago(iso: str | None) -> str:
    if not iso:
        return "never"
    then = datetime.fromisoformat(iso)
    if then.tzinfo is None:
        then = then.replace(tzinfo=UTC)
    secs = (datetime.now(UTC) - then).total_seconds()
    if secs < 90:
        return "just now"
    if secs < 3600:
        return f"{int(secs // 60)} min ago"
    if secs < 86400:
        return f"{int(secs // 3600)} hr ago"
    days = int(secs // 86400)
    return "yesterday" if days == 1 else f"{days} days ago"


def date_span(ev) -> str:
    from .events import format_range
    return format_range(datetime.fromisoformat(ev["start_at"]), datetime.fromisoformat(ev["end_at"]))


def create_app(settings: Settings, pipeline: Pipeline) -> FastAPI:
    app = FastAPI(title="Highlights", docs_url=None, redoc_url=None)
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
    templates = Jinja2Templates(directory=HERE / "templates")
    env = templates.env
    env.filters.update(gb=gb, minutes=minutes, span=span, ago=ago)
    env.globals.update(STEPS=STEPS, STEP_OF=STEP_OF, STAGE_LABEL=STAGE_LABEL, date_span=date_span)
    thumb_dir = settings.data_dir / "thumbs"
    thumb_dir.mkdir(parents=True, exist_ok=True)

    def base(request: Request) -> str:
        return request.scope.get("root_path", "").rstrip("/")

    def go(request: Request, path: str) -> RedirectResponse:
        return RedirectResponse(base(request) + path, status_code=303)

    def page(request: Request, name: str, status_code: int = 200, **ctx) -> Response:
        ctx.update(
            base=base(request),
            immich=settings.immich_link,
            missing=settings.missing(),
            cleanup_enabled=settings.cleanup_enabled,
            status_code=status_code,
        )
        return templates.TemplateResponse(request, name, ctx, status_code=status_code)

    def event_or_404(event_id: int):
        ev = db.get_event(event_id)
        if ev is None:
            raise HTTPException(404, "That highlight no longer exists")
        return ev

    # --- pages ---

    @app.get("/")
    def home(request: Request, tab: str = "trips"):
        all_events = db.list_events()
        needs = [e for e in all_events if e["stage"] in ("picks_ready", "ready")
                 or (e["error"] and e["stage"] == "found")]
        working = [e for e in all_events if e["stage"] in db.ACTIVE_STAGES]
        found = [e for e in all_events if e["stage"] == "found" and not e["error"]]
        trips = [e for e in found if e["kind"] == "trip"]
        months = [e for e in found if e["kind"] == "month"]
        done = [e for e in all_events if e["stage"] == "done"]
        skipped = [e for e in all_events if e["stage"] == "dismissed"]
        jobs = {j["event_id"]: j for j in db.active_jobs()}
        return page(
            request, "home.html", needs=needs, working=working, trips=trips, months=months,
            done=done, skipped=skipped, jobs=jobs, tab=tab if tab in ("trips", "months") else "trips",
            last_scan=db.get_meta("last_scan_at"), library_count=db.get_meta("library_count"),
            scan_job=jobs.get(None), freed=sum(e["freed_bytes"] or 0 for e in done),
        )

    @app.get("/events/{event_id}")
    def event_page(request: Request, event_id: int, confirm: int = 0):
        ev = event_or_404(event_id)
        picks = db.picks(event_id)
        candidates = None
        if ev["stage"] == "ready" and confirm:
            try:
                candidates = pipeline.cleanup_candidates(event_id)
            except Exception as e:  # noqa: BLE001
                db.update_event(event_id, error=f"Couldn't check the raw clips: {e}")
                ev = db.get_event(event_id)
        return page(
            request, "event.html", ev=ev, picks=picks, job=db.active_job(event_id),
            log=db.activity(event_id, 30), confirm=bool(confirm), candidates=candidates,
            cleanup_bytes=sum(c.get("size_bytes") or 0 for c in candidates or []),
            clip_count=sum(1 for p in picks if p["kind"] == "clip"),
            photo_count=sum(1 for p in picks if p["kind"] == "photo"),
            pick_seconds=sum(p["duration_s"] for p in picks),
            has_video=bool((p := settings.from_stored(ev["highlight_path"])) and p.exists()),
        )

    @app.get("/activity")
    def activity_page(request: Request):
        return page(request, "activity.html", log=db.activity(None, 200))

    # --- actions ---

    @app.post("/scan")
    def scan(request: Request):
        start_job("scan")
        return go(request, "/")

    def require_stage(ev, *stages: str) -> None:
        if ev["stage"] not in stages:
            raise HTTPException(409, f"This highlight is at '{STAGE_LABEL[ev['stage']]}' now")

    @app.post("/events/{event_id}/pick")
    def pick(request: Request, event_id: int):
        ev = event_or_404(event_id)
        require_stage(ev, "found", "picks_ready")
        db.update_event(event_id, error=None)
        start_job("pick", event_id)
        db.log("Asked Claude to pick moments", event_id)
        return go(request, f"/events/{event_id}")

    @app.post("/events/{event_id}/render")
    def render(request: Request, event_id: int):
        ev = event_or_404(event_id)
        require_stage(ev, "picks_ready", "ready")
        db.update_event(event_id, error=None)
        start_job("render", event_id)
        db.log("Started rendering", event_id)
        return go(request, f"/events/{event_id}")

    @app.post("/events/{event_id}/cleanup")
    def cleanup(request: Request, event_id: int):
        ev = event_or_404(event_id)
        require_stage(ev, "ready")
        if not settings.cleanup_enabled:
            raise HTTPException(409, "Cleanup is off until the Immich backup is set up")
        db.update_event(event_id, error=None)
        start_job("cleanup", event_id)
        return go(request, f"/events/{event_id}")

    @app.post("/events/{event_id}/finish")
    def finish(request: Request, event_id: int):
        ev = event_or_404(event_id)
        require_stage(ev, "ready")
        db.set_stage(event_id, "done")
        db.log("Finished and kept the raw clips", event_id)
        return go(request, f"/events/{event_id}")

    @app.post("/events/{event_id}/back")
    def back_to_picks(request: Request, event_id: int):
        ev = event_or_404(event_id)
        require_stage(ev, "ready")
        db.set_stage(event_id, "picks_ready")
        db.log("Went back to change the picks", event_id)
        return go(request, f"/events/{event_id}")

    @app.post("/events/{event_id}/dismiss")
    def dismiss(request: Request, event_id: int):
        ev = event_or_404(event_id)
        require_stage(ev, "found", "picks_ready")
        db.set_stage(event_id, "dismissed")
        db.log("Skipped this one", event_id)
        return go(request, "/")

    @app.post("/events/{event_id}/restore")
    def restore(request: Request, event_id: int):
        ev = event_or_404(event_id)
        require_stage(ev, "dismissed")
        db.set_stage(event_id, "picks_ready" if db.picks(event_id) else "found")
        return go(request, f"/events/{event_id}")

    # --- data ---

    @app.get("/thumb/{asset_id}")
    def thumb(asset_id: str, size: str = "thumbnail"):
        if size not in ("thumbnail", "preview") or not asset_id.replace("-", "").isalnum():
            raise HTTPException(400)
        cached = thumb_dir / f"{asset_id}-{size}"
        if cached.exists():
            data = cached.read_bytes()
            media_type = (cached.with_suffix(".type").read_text()
                          if cached.with_suffix(".type").exists() else "image/jpeg")
        else:
            try:
                data, media_type = pipeline.immich.thumbnail(asset_id, size)
            except Exception as e:  # noqa: BLE001
                raise HTTPException(404) from e
            cached.write_bytes(data)
            cached.with_suffix(".type").write_text(media_type)
        return Response(data, media_type=media_type,
                        headers={"Cache-Control": "public, max-age=604800, immutable"})

    @app.get("/events/{event_id}/video")
    def video(event_id: int):
        ev = event_or_404(event_id)
        path = settings.from_stored(ev["highlight_path"])
        if not path or not path.exists():
            raise HTTPException(404, "The rendered file is gone; it's still in Immich")
        return FileResponse(path, media_type="video/mp4")

    @app.get("/api/status")
    def status():
        jobs = db.active_jobs()
        return JSONResponse({
            "stages": db.stage_counts(),
            "jobs": [{"id": j["id"], "kind": j["kind"], "event_id": j["event_id"],
                      "status": j["status"], "progress": j["progress"], "message": j["message"]}
                     for j in jobs],
        }, headers={"Cache-Control": "no-store"})

    @app.get("/api/events/{event_id}")
    def event_status(event_id: int):
        ev = event_or_404(event_id)
        job = db.active_job(event_id)
        return JSONResponse({
            "stage": ev["stage"], "error": ev["error"],
            "progress": job["progress"] if job else None,
            "message": job["message"] if job else None,
            "queued": bool(job and job["status"] == "queued"),
        }, headers={"Cache-Control": "no-store"})

    # --- PWA plumbing ---

    @app.get("/manifest.webmanifest")
    def manifest(request: Request):
        b = base(request)
        return JSONResponse({
            "name": "Highlights", "short_name": "Highlights",
            "description": "Trip and month highlight videos from your Immich library",
            "start_url": f"{b}/", "scope": f"{b}/", "display": "standalone",
            "background_color": "#14110f", "theme_color": "#14110f",
            "icons": [
                {"src": f"{b}/static/icon-192.png", "sizes": "192x192", "type": "image/png"},
                {"src": f"{b}/static/icon-512.png", "sizes": "512x512", "type": "image/png"},
                {"src": f"{b}/static/icon-maskable.png", "sizes": "512x512", "type": "image/png",
                 "purpose": "maskable"},
            ],
        }, media_type="application/manifest+json")

    @app.get("/sw.js")
    def service_worker():
        return FileResponse(HERE / "static" / "sw.js", media_type="text/javascript",
                            headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "./"})

    @app.exception_handler(HTTPException)
    def http_error(request: Request, exc: HTTPException):
        if request.url.path.startswith("/api/") or request.method == "GET" and exc.status_code < 500 \
                and request.url.path.startswith(("/thumb/", "/static/")):
            return JSONResponse({"error": exc.detail}, status_code=exc.status_code)
        return page(request, "error.html", status_code=exc.status_code, message=exc.detail)

    return app
