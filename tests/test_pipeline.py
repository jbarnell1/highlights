from dataclasses import replace
from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient
from test_events import HOME, home_days, trip

from highlights import db, picker
from highlights.config import Settings
from highlights.immich import FakeImmich
from highlights.pipeline import Pipeline
from highlights.web import create_app


def noop(_f, _m):
    pass


@pytest.fixture
def setup(tmp_path, monkeypatch):
    settings = replace(Settings(), data_dir=tmp_path, immich_api_key="k", claude_token="k",
                       home_lat=HOME[0], home_lon=HOME[1], cleanup_enabled=True)
    db.init(settings.db_path)
    assets = home_days(datetime(2022, 5, 1), 25) + trip(datetime(2022, 5, 29), 6)
    immich = FakeImmich(assets)
    pipe = Pipeline(settings, immich, claude=object(), encoder="libx264")
    # Contact sheets need real files; the picking logic is what's under test here.
    monkeypatch.setattr(pipe, "_video_sheets", lambda eid, vids, prog, **kw: [
        picker.SheetVideo(f"V{kw.get('start_ref', 1) + i}", v["id"], 30.0, b"") for i, v in enumerate(vids)
    ])
    monkeypatch.setattr(pipe, "_photo_sheets", lambda photos, prog, **kw: [
        picker.SheetPhotos([(f"P{i + 1}", p["id"]) for i, p in enumerate(photos)], b"")
    ])
    return settings, immich, pipe


def fake_claude(monkeypatch, clips, photos):
    def ask(client, model, content):
        return picker.Picks(clips=[picker.ClipPick(**c) for c in clips],
                            photos=[picker.PhotoPick(**p) for p in photos], notes="test")
    monkeypatch.setattr(picker, "ask_claude", ask)


def trip_event_id(pipe):
    pipe.scan(noop, today=date(2022, 8, 1))
    return next(e["id"] for e in db.list_events() if e["kind"] == "trip")


def test_scan_is_idempotent(setup):
    _, _, pipe = setup
    pipe.scan(noop, today=date(2022, 8, 1))
    first = len(db.list_events())
    result = pipe.scan(noop, today=date(2022, 8, 1))
    assert result["new"] == 0 and len(db.list_events()) == first


def test_pick_resolves_refs_and_clamps_times(setup, monkeypatch):
    _, immich, pipe = setup
    eid = trip_event_id(pipe)
    fake_claude(monkeypatch, [
        {"ref": "V1", "start": 28.0, "duration": 6.0, "why": "wave"},   # runs past the end
        {"ref": "V99", "start": 0, "duration": 4, "why": "not a real ref"},
    ], [{"ref": "P2", "why": "smile"}, {"ref": "P2", "why": "dupe"}])
    pipe.pick(eid, noop)
    picks = db.picks(eid)
    clips = [p for p in picks if p["kind"] == "clip"]
    assert len(clips) == 1 and clips[0]["start_s"] == 24.0 and clips[0]["duration_s"] == 6.0
    assert len([p for p in picks if p["kind"] == "photo"]) == 1
    ev = db.get_event(eid)
    assert ev["album_id"] and set(immich.album_members[ev["album_id"]]) == {p["asset_id"] for p in picks}


def test_reconcile_follows_album_edits(setup, monkeypatch):
    _, immich, pipe = setup
    eid = trip_event_id(pipe)
    fake_claude(monkeypatch, [{"ref": "V1", "start": 2, "duration": 5, "why": "a"}],
                [{"ref": "P1", "why": "b"}, {"ref": "P2", "why": "c"}])
    pipe.pick(eid, noop)
    album = db.get_event(eid)["album_id"]
    photo_ids = [p["asset_id"] for p in db.picks(eid) if p["kind"] == "photo"]
    immich.album_members[album].remove(photo_ids[0])          # user removed a photo
    extra_video = next(r["asset_id"] for r in db.event_assets(eid, "VIDEO")
                       if r["asset_id"] not in immich.album_members[album])
    immich.add_to_album(album, [extra_video])                 # and added a clip
    fake_claude(monkeypatch, [], [])                          # Claude returns nothing: use the middle
    rows = pipe.reconcile(eid, noop)
    ids = {r["asset_id"] for r in rows}
    assert photo_ids[0] not in ids and extra_video in ids
    added = next(r for r in rows if r["asset_id"] == extra_video)
    assert added["source"] == "added" and added["duration_s"] == 6.0


def test_cleanup_keeps_favorites_and_other_albums(setup):
    _, immich, pipe = setup
    eid = trip_event_id(pipe)
    videos = [r["asset_id"] for r in db.event_assets(eid, "VIDEO")]
    immich.assets[videos[0]]["is_favorite"] = True
    immich.create_album("Best of 2022", [videos[1]])
    doomed = {a["id"] for a in pipe.cleanup_candidates(eid)}
    assert videos[0] not in doomed and videos[1] not in doomed
    assert doomed == set(videos[2:])
    pipe.cleanup(eid, noop)
    assert set(immich.trashed) == doomed
    assert db.get_event(eid)["freed_bytes"] == len(doomed) * 1_000_000


def test_cleanup_refuses_when_disabled(setup):
    settings, immich, pipe = setup
    pipe.s = replace(settings, cleanup_enabled=False)
    eid = trip_event_id(pipe)
    with pytest.raises(RuntimeError, match="turned off"):
        pipe.cleanup(eid, noop)
    assert immich.trashed == []


def test_pages_render_at_every_stage(setup, monkeypatch):
    settings, _, pipe = setup
    eid = trip_event_id(pipe)
    client = TestClient(create_app(settings, pipe), root_path="/highlights")
    home = client.get("/")
    assert home.status_code == 200 and "Ready for a highlight" in home.text
    assert 'href="/highlights/events/' in home.text
    for stage in ("found", "picks_ready", "ready", "done", "dismissed", "rendering"):
        db.set_stage(eid, stage)
        r = client.get(f"/events/{eid}")
        assert r.status_code == 200, stage
    r = client.get(f"/events/{eid}?confirm=1")
    assert r.status_code == 200
    assert client.get("/manifest.webmanifest").json()["start_url"] == "/highlights/"
    assert client.get("/events/99999").status_code == 404
    db.set_stage(eid, "found")
    r = client.post(f"/events/{eid}/render", follow_redirects=False)
    assert r.status_code == 409
