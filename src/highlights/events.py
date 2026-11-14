"""Find trips and months in a list of assets. Pure functions, no I/O.

A trip is a run of photos taken far from home with no long gap between them, so a vacation that
crosses a month boundary stays one event. Everything else is grouped by calendar month, minus the
trip days, so nothing lands in two highlights.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

TRIP_MAX_GAP = timedelta(hours=48)
TRIP_MIN_ASSETS = 12
TRIP_MIN_SPAN = timedelta(hours=12)
MONTH_MIN_ASSETS = 8
NEIGHBOR_WINDOW = timedelta(hours=12)


@dataclass
class Event:
    key: str
    kind: str  # "trip" | "month"
    title: str
    place: str | None
    start: datetime
    end: datetime
    assets: list[dict] = field(default_factory=list)

    def summary(self) -> dict:
        videos = [a for a in self.assets if a["type"] == "VIDEO"]
        photos = [a for a in self.assets if a["type"] == "IMAGE"]
        return {
            "key": self.key,
            "kind": self.kind,
            "title": self.title,
            "place": self.place,
            "start_at": self.start.isoformat(timespec="seconds"),
            "end_at": self.end.isoformat(timespec="seconds"),
            "photo_count": len(photos),
            "video_count": len(videos),
            "video_seconds": sum((a.get("duration_ms") or 0) for a in videos) / 1000,
            "video_bytes": sum((a.get("size_bytes") or 0) for a in videos),
            "cover_asset_id": pick_cover(self.assets),
        }


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value[:19])


def infer_home(assets: list[dict]) -> tuple[float, float] | None:
    """The most common ~10 km grid cell among geotagged assets."""
    cells = Counter(
        (round(a["lat"], 1), round(a["lon"], 1))
        for a in assets
        if a.get("lat") is not None and a.get("lon") is not None
    )
    if not cells:
        return None
    (lat, lon), _ = cells.most_common(1)[0]
    return lat, lon


def pick_cover(assets: list[dict]) -> str | None:
    photos = [a for a in assets if a["type"] == "IMAGE"]
    pool = [a for a in photos if a.get("is_favorite")] or photos or assets
    if not pool:
        return None
    return pool[len(pool) // 2]["id"]


def _place_name(assets: list[dict]) -> str | None:
    """A US trip is named by state, anywhere else by country; the city when it's one city."""
    cities = Counter(a.get("city") for a in assets if a.get("city"))
    states = Counter(a.get("state") for a in assets if a.get("state"))
    countries = Counter(a.get("country") for a in assets if a.get("country"))
    if not countries:
        return None
    country = countries.most_common(1)[0][0]
    if len(cities) == 1:
        return next(iter(cities))
    if country in ("United States", "United States of America", "USA") and states:
        top = [s for s, _ in states.most_common(2)]
        return " & ".join(top) if len(top) == 2 and states[top[1]] >= 0.25 * len(assets) else top[0]
    return country


def format_range(start: datetime, end: datetime) -> str:
    s, e = start.date(), end.date()
    if s == e:
        return f"{s:%b} {s.day}, {s.year}"
    if s.year != e.year:
        return f"{s:%b} {s.day}, {s.year} – {e:%b} {e.day}, {e.year}"
    if s.month == e.month:
        return f"{s:%b} {s.day}–{e.day}, {s.year}"
    return f"{s:%b} {s.day} – {e:%b} {e.day}, {s.year}"


def _away_flags(assets: list[dict], home: tuple[float, float] | None, away_km: float) -> list[bool]:
    """Whether each asset was taken away from home. Untagged assets borrow from a close neighbor."""
    n = len(assets)
    known: list[bool | None] = []
    for a in assets:
        if home is None or a.get("lat") is None or a.get("lon") is None:
            known.append(None)
        else:
            known.append(haversine_km(home[0], home[1], a["lat"], a["lon"]) > away_km)
    times = [parse_time(a["taken_at"]) for a in assets]
    flags = []
    for i in range(n):
        if known[i] is not None:
            flags.append(bool(known[i]))
            continue
        best: tuple[timedelta, bool] | None = None
        for j in range(max(0, i - 50), min(n, i + 51)):
            if known[j] is None:
                continue
            gap = abs(times[j] - times[i])
            if gap <= NEIGHBOR_WINDOW and (best is None or gap < best[0]):
                best = (gap, bool(known[j]))
        flags.append(best[1] if best else False)
    return flags


def find_events(
    assets: list[dict],
    home: tuple[float, float] | None,
    away_km: float = 80,
    today: date | None = None,
) -> list[Event]:
    """Group assets into trips and finished months. Months still in progress are left out."""
    today = today or date.today()
    assets = sorted(assets, key=lambda a: a["taken_at"])
    if not assets:
        return []
    flags = _away_flags(assets, home, away_km)
    times = [parse_time(a["taken_at"]) for a in assets]

    # Runs of away assets, split wherever the gap between two away assets is too long.
    runs: list[list[int]] = []
    for i, away in enumerate(flags):
        if not away:
            continue
        if runs and times[i] - times[runs[-1][-1]] <= TRIP_MAX_GAP:
            runs[-1].append(i)
        else:
            runs.append([i])

    events: list[Event] = []
    in_trip: set[int] = set()
    for run in runs:
        first, last = run[0], run[-1]
        span = times[last] - times[first]
        idx = list(range(first, last + 1))  # include home-flagged assets between away ones
        if len(idx) < TRIP_MIN_ASSETS or span < TRIP_MIN_SPAN:
            continue
        # A trip still going on (last photo within the gap window of today) waits until it ends.
        if datetime.combine(today, datetime.min.time()) - times[last] < TRIP_MAX_GAP:
            continue
        members = [assets[i] for i in idx]
        place = _place_name([assets[i] for i in run])
        start, end = times[first], times[last]
        title = f"{place} · {format_range(start, end)}" if place else f"Trip · {format_range(start, end)}"
        events.append(Event(
            key=f"trip:{start:%Y-%m-%d}", kind="trip", title=title, place=place,
            start=start, end=end, assets=members,
        ))
        in_trip.update(idx)

    by_month: dict[tuple[int, int], list[int]] = {}
    for i in range(len(assets)):
        if i in in_trip:
            continue
        by_month.setdefault((times[i].year, times[i].month), []).append(i)
    for (year, month), idx in by_month.items():
        if (year, month) >= (today.year, today.month) or len(idx) < MONTH_MIN_ASSETS:
            continue
        start = datetime(year, month, 1)
        title = f"{start:%B %Y}"
        events.append(Event(
            key=f"month:{year:04d}-{month:02d}", kind="month", title=title, place=None,
            start=times[idx[0]], end=times[idx[-1]], assets=[assets[i] for i in idx],
        ))

    events.sort(key=lambda e: e.start)
    return events
