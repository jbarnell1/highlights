"""SQLite storage. All SQL lives here; the rest of the app calls these functions."""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    key TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    place TEXT,
    start_at TEXT NOT NULL,
    end_at TEXT NOT NULL,
    stage TEXT NOT NULL DEFAULT 'found',
    photo_count INTEGER NOT NULL DEFAULT 0,
    video_count INTEGER NOT NULL DEFAULT 0,
    video_seconds REAL NOT NULL DEFAULT 0,
    video_bytes INTEGER NOT NULL DEFAULT 0,
    cover_asset_id TEXT,
    album_id TEXT,
    highlight_asset_id TEXT,
    highlight_path TEXT,
    highlight_seconds REAL,
    highlight_bytes INTEGER,
    freed_bytes INTEGER,
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    stage_changed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS event_assets (
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    asset_id TEXT NOT NULL,
    type TEXT NOT NULL,
    taken_at TEXT NOT NULL,
    duration_ms INTEGER,
    size_bytes INTEGER,
    is_favorite INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (event_id, asset_id)
);
CREATE TABLE IF NOT EXISTS picks (
    id INTEGER PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    asset_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    start_s REAL NOT NULL DEFAULT 0,
    duration_s REAL NOT NULL,
    taken_at TEXT NOT NULL,
    why TEXT,
    source TEXT NOT NULL DEFAULT 'claude'
);
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL,
    event_id INTEGER,
    prev_stage TEXT,
    status TEXT NOT NULL DEFAULT 'queued',
    progress REAL NOT NULL DEFAULT 0,
    message TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT
);
CREATE TABLE IF NOT EXISTS activity (
    id INTEGER PRIMARY KEY,
    at TEXT NOT NULL,
    event_id INTEGER,
    message TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE INDEX IF NOT EXISTS ix_events_stage ON events(stage);
CREATE INDEX IF NOT EXISTS ix_jobs_status ON jobs(status);
"""

# Stages, in pipeline order. "failed" and "dismissed" sit outside the line.
STAGES = ["found", "picking", "picks_ready", "rendering", "ready", "cleaning", "done"]
ACTIVE_STAGES = {"picking", "rendering", "cleaning"}

_lock = threading.Lock()
_path: Path | None = None


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def init(path: Path) -> None:
    global _path
    path.parent.mkdir(parents=True, exist_ok=True)
    _path = path
    with connect() as con:
        con.executescript(SCHEMA)


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    if _path is None:
        raise RuntimeError("db.init() has not been called")
    con = sqlite3.connect(_path, timeout=30, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")
    try:
        with _lock:
            yield con
            con.commit()
    finally:
        con.close()


# --- events -----------------------------------------------------------------------------------


def get_event(event_id: int) -> sqlite3.Row | None:
    with connect() as con:
        return con.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()


def get_event_by_key(key: str) -> sqlite3.Row | None:
    with connect() as con:
        return con.execute("SELECT * FROM events WHERE key = ?", (key,)).fetchone()


def list_events(stages: Iterable[str] | None = None, limit: int = 500) -> list[sqlite3.Row]:
    with connect() as con:
        if stages is None:
            sql = "SELECT * FROM events ORDER BY start_at DESC LIMIT ?"
            return con.execute(sql, (limit,)).fetchall()
        stages = list(stages)
        marks = ",".join("?" for _ in stages)
        sql = f"SELECT * FROM events WHERE stage IN ({marks}) ORDER BY start_at DESC LIMIT ?"
        return con.execute(sql, (*stages, limit)).fetchall()


def upsert_event(fields: dict, assets: list[dict]) -> tuple[int, bool]:
    """Insert a new event or refresh an untouched one. Returns (id, created).

    Events past the 'found' stage keep their asset list: the user already acted on them.
    """
    ts = now()
    with connect() as con:
        row = con.execute("SELECT id, stage FROM events WHERE key = ?", (fields["key"],)).fetchone()
        if row and row["stage"] not in ("found", "dismissed"):
            return row["id"], False
        cols = [
            "kind", "title", "place", "start_at", "end_at", "photo_count", "video_count",
            "video_seconds", "video_bytes", "cover_asset_id",
        ]
        if row:
            sets = ", ".join(f"{c} = ?" for c in cols)
            con.execute(
                f"UPDATE events SET {sets}, updated_at = ? WHERE id = ?",
                (*[fields[c] for c in cols], ts, row["id"]),
            )
            event_id, created = row["id"], False
            con.execute("DELETE FROM event_assets WHERE event_id = ?", (event_id,))
        else:
            cur = con.execute(
                f"INSERT INTO events (key, {', '.join(cols)}, created_at, updated_at, "
                f"stage_changed_at) VALUES (?, {', '.join('?' for _ in cols)}, ?, ?, ?)",
                (fields["key"], *[fields[c] for c in cols], ts, ts, ts),
            )
            event_id, created = cur.lastrowid, True
        con.executemany(
            "INSERT OR REPLACE INTO event_assets (event_id, asset_id, type, taken_at, duration_ms,"
            " size_bytes, is_favorite) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    event_id, a["id"], a["type"], a["taken_at"], a.get("duration_ms"),
                    a.get("size_bytes"), int(bool(a.get("is_favorite"))),
                )
                for a in assets
            ],
        )
        return event_id, created


def set_stage(event_id: int, stage: str, error: str | None = None) -> None:
    ts = now()
    with connect() as con:
        con.execute(
            "UPDATE events SET stage = ?, error = ?, updated_at = ?, stage_changed_at = ? "
            "WHERE id = ?",
            (stage, error, ts, ts, event_id),
        )


def update_event(event_id: int, **fields) -> None:
    if not fields:
        return
    sets = ", ".join(f"{k} = ?" for k in fields)
    with connect() as con:
        con.execute(
            f"UPDATE events SET {sets}, updated_at = ? WHERE id = ?",
            (*fields.values(), now(), event_id),
        )


def event_assets(event_id: int, asset_type: str | None = None) -> list[sqlite3.Row]:
    with connect() as con:
        if asset_type:
            return con.execute(
                "SELECT * FROM event_assets WHERE event_id = ? AND type = ? ORDER BY taken_at",
                (event_id, asset_type),
            ).fetchall()
        return con.execute(
            "SELECT * FROM event_assets WHERE event_id = ? ORDER BY taken_at", (event_id,)
        ).fetchall()


def stage_counts() -> dict[str, int]:
    with connect() as con:
        rows = con.execute("SELECT stage, COUNT(*) AS n FROM events GROUP BY stage").fetchall()
    return {r["stage"]: r["n"] for r in rows}


# --- picks ------------------------------------------------------------------------------------


def replace_picks(event_id: int, picks: list[dict]) -> None:
    with connect() as con:
        con.execute("DELETE FROM picks WHERE event_id = ?", (event_id,))
        con.executemany(
            "INSERT INTO picks (event_id, asset_id, kind, start_s, duration_s, taken_at, why, source)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    event_id, p["asset_id"], p["kind"], p.get("start_s", 0.0), p["duration_s"],
                    p["taken_at"], p.get("why"), p.get("source", "claude"),
                )
                for p in picks
            ],
        )


def picks(event_id: int) -> list[sqlite3.Row]:
    with connect() as con:
        return con.execute(
            "SELECT * FROM picks WHERE event_id = ? ORDER BY taken_at, start_s", (event_id,)
        ).fetchall()


# --- jobs -------------------------------------------------------------------------------------


def enqueue(kind: str, event_id: int | None = None, prev_stage: str | None = None) -> int:
    with connect() as con:
        existing = con.execute(
            "SELECT id FROM jobs WHERE kind = ? AND event_id IS ? AND status IN ('queued','running')",
            (kind, event_id),
        ).fetchone()
        if existing:
            return existing["id"]
        cur = con.execute(
            "INSERT INTO jobs (kind, event_id, prev_stage, created_at) VALUES (?, ?, ?, ?)",
            (kind, event_id, prev_stage, now()),
        )
        return cur.lastrowid


def claim_next_job() -> sqlite3.Row | None:
    with connect() as con:
        row = con.execute(
            "SELECT * FROM jobs WHERE status = 'queued' ORDER BY id LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        con.execute(
            "UPDATE jobs SET status = 'running', started_at = ? WHERE id = ?", (now(), row["id"])
        )
        return row


def update_job(job_id: int, **fields) -> None:
    sets = ", ".join(f"{k} = ?" for k in fields)
    with connect() as con:
        con.execute(f"UPDATE jobs SET {sets} WHERE id = ?", (*fields.values(), job_id))


def finish_job(job_id: int, error: str | None = None) -> None:
    status = "failed" if error else "done"
    with connect() as con:
        con.execute(
            "UPDATE jobs SET status = ?, error = ?, finished_at = ?, progress = ? WHERE id = ?",
            (status, error, now(), 0 if error else 1, job_id),
        )


def requeue_interrupted_jobs() -> int:
    """Jobs left 'running' by a crash or restart go back in the queue."""
    with connect() as con:
        cur = con.execute("UPDATE jobs SET status = 'queued' WHERE status = 'running'")
        return cur.rowcount


def active_job(event_id: int | None) -> sqlite3.Row | None:
    with connect() as con:
        return con.execute(
            "SELECT * FROM jobs WHERE event_id IS ? AND status IN ('queued','running') "
            "ORDER BY id DESC LIMIT 1",
            (event_id,),
        ).fetchone()


def active_jobs() -> list[sqlite3.Row]:
    with connect() as con:
        return con.execute(
            "SELECT * FROM jobs WHERE status IN ('queued','running') ORDER BY id"
        ).fetchall()


# --- activity and meta ------------------------------------------------------------------------


def log(message: str, event_id: int | None = None) -> None:
    with connect() as con:
        con.execute(
            "INSERT INTO activity (at, event_id, message) VALUES (?, ?, ?)",
            (now(), event_id, message),
        )


def activity(event_id: int | None = None, limit: int = 100) -> list[sqlite3.Row]:
    with connect() as con:
        if event_id is None:
            return con.execute(
                "SELECT a.*, e.title FROM activity a LEFT JOIN events e ON e.id = a.event_id "
                "ORDER BY a.id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return con.execute(
            "SELECT * FROM activity WHERE event_id = ? ORDER BY id DESC LIMIT ?",
            (event_id, limit),
        ).fetchall()


def get_meta(key: str) -> str | None:
    with connect() as con:
        row = con.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None


def set_meta(key: str, value: str) -> None:
    with connect() as con:
        con.execute(
            "INSERT INTO meta (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
