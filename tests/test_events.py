from datetime import date, datetime, timedelta

from highlights.events import find_events, format_range, haversine_km, infer_home

HOME = (39.74, -104.99)  # Denver (any two far-apart cities work)
BEACH = (32.72, -117.16)  # San Diego


def asset(i, when, where=None, kind="IMAGE", city=None, state=None, country=None, dur=None):
    lat, lon = where if where else (None, None)
    return {
        "id": f"a{i}", "type": kind, "taken_at": when.isoformat(timespec="seconds"),
        "lat": lat, "lon": lon, "city": city, "state": state, "country": country,
        "duration_ms": dur, "size_bytes": 1_000_000, "is_favorite": False,
    }


def home_days(start, days, per_day=3, first_id=0):
    out = []
    for d in range(days):
        for k in range(per_day):
            out.append(asset(first_id + d * per_day + k, start + timedelta(days=d, hours=9 + k * 3),
                             HOME, city="Denver", state="Colorado", country="United States"))
    return out


def trip(start, days, per_day=6, first_id=1000, where=BEACH):
    out = []
    for d in range(days):
        for k in range(per_day):
            out.append(asset(first_id + d * per_day + k, start + timedelta(days=d, hours=8 + k * 2),
                             where, kind="VIDEO" if k == 0 else "IMAGE", dur=30000 if k == 0 else None,
                             city="San Diego", state="California", country="United States"))
    return out


def test_haversine_known_distance():
    assert 1300 < haversine_km(*HOME, *BEACH) < 1500


def test_trip_across_month_boundary_is_one_event():
    assets = home_days(datetime(2022, 5, 1), 25) + trip(datetime(2022, 5, 29), 6) + \
        home_days(datetime(2022, 6, 6), 20, first_id=500)
    events = find_events(assets, HOME, today=date(2022, 8, 1))
    trips = [e for e in events if e.kind == "trip"]
    assert len(trips) == 1
    t = trips[0]
    assert t.start.date() == date(2022, 5, 29) and t.end.date() == date(2022, 6, 3)
    assert t.title == "San Diego · May 29 – Jun 3, 2022"
    months = {e.key for e in events if e.kind == "month"}
    assert months == {"month:2022-05", "month:2022-06"}
    trip_ids = {a["id"] for a in t.assets}
    for m in (e for e in events if e.kind == "month"):
        assert not trip_ids & {a["id"] for a in m.assets}, "trip photos must not repeat in a month"


def test_untagged_photos_follow_their_neighbors():
    assets = trip(datetime(2023, 3, 1), 3)
    assets.append(asset(9999, datetime(2023, 3, 2, 11, 30)))  # no GPS, middle of the trip
    events = find_events(assets, HOME, today=date(2023, 6, 1))
    assert any("a9999" in {a["id"] for a in e.assets} for e in events if e.kind == "trip")


def test_short_outing_is_not_a_trip():
    assets = home_days(datetime(2023, 4, 1), 20) + [
        asset(2000 + i, datetime(2023, 4, 10, 10 + i // 6, i % 6 * 10), BEACH) for i in range(14)
    ]
    events = find_events(assets, HOME, today=date(2023, 6, 1))
    assert not [e for e in events if e.kind == "trip"]


def test_current_month_and_ongoing_trip_wait():
    today = date(2024, 7, 20)
    assets = home_days(datetime(2024, 7, 1), 15) + trip(datetime(2024, 7, 17), 3)
    events = find_events(assets, HOME, today=today)
    assert events == []


def test_infer_home_picks_most_common_cell():
    assets = home_days(datetime(2022, 1, 1), 10) + trip(datetime(2022, 2, 1), 2)
    lat, lon = infer_home(assets)
    assert abs(lat - HOME[0]) < 0.1 and abs(lon - HOME[1]) < 0.1


def test_format_range():
    assert format_range(datetime(2022, 5, 29), datetime(2022, 6, 3)) == "May 29 – Jun 3, 2022"
    assert format_range(datetime(2022, 5, 2), datetime(2022, 5, 9)) == "May 2–9, 2022"
    assert format_range(datetime(2022, 12, 30), datetime(2023, 1, 2)) == "Dec 30, 2022 – Jan 2, 2023"
