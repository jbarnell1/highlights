"""The pipeline steps. Web routes enqueue jobs; the worker calls these functions."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from datetime import date, datetime, timedelta
from pathlib import Path

from . import db, events, media, picker
from .config import Settings

Progress = Callable[[float, str], None]

ALBUM_PREFIX = "Highlight · "
HIGHLIGHTS_ALBUM = "Highlights"
SCAN_START = "1990-01-01T00:00:00.000Z"


class Pipeline:
    def __init__(self, settings: Settings, immich, claude=None, encoder: str | None = None):
        self.s = settings
        self.immich = immich
        self.claude = claude
        self._encoder = encoder

    @property
    def encoder(self) -> str:
        if self._encoder is None:
            self._encoder = media.detect_encoder(self.s.ffmpeg, self.s.qsv_device)
        return self._encoder

    def work(self, event_id: int, *parts: str) -> Path:
        path = self.s.work_dir / f"event-{event_id}"
        for p in parts:
            path = path / p
        path.mkdir(parents=True, exist_ok=True)
        return path

    # --- scan -----------------------------------------------------------------------------

    def scan(self, progress: Progress, today: date | None = None) -> dict:
        progress(0.05, "Reading your library from Immich")
        assets = [a for a in self.immich.search_assets(taken_after=SCAN_START)
                  if not a.get("is_trashed")]
        progress(0.6, f"Grouping {len(assets):,} photos and videos")
        home = None
        if self.s.home_lat is not None and self.s.home_lon is not None:
            home = (self.s.home_lat, self.s.home_lon)
        else:
            home = events.infer_home(assets)
        if home:
            db.set_meta("home", f"{home[0]:.3f},{home[1]:.3f}")
        found = events.find_events(assets, home, self.s.away_km, today=today)
        new = 0
        for ev in found:
            _, created = db.upsert_event(ev.summary(), ev.assets)
            new += int(created)
        db.set_meta("last_scan_at", db.now())
        db.set_meta("library_count", str(len(assets)))
        trips = sum(1 for e in found if e.kind == "trip")
        msg = f"Scanned {len(assets):,} items: {trips} trips, {len(found) - trips} months"
        msg += f", {new} new" if new else ", nothing new"
        db.log(msg)
        return {"assets": len(assets), "events": len(found), "new": new}

    # --- pick -----------------------------------------------------------------------------

    def _live_assets(self, event_id: int, asset_type: str | None = None) -> list[dict]:
        """The event's assets as Immich has them now, minus anything deleted or trashed.

        Immich filters by UTC instant while events store local wall-clock times, so the search
        window is padded by a day on each side and then narrowed to the event's own ids.
        """
        rows = db.event_assets(event_id, asset_type)
        if not rows:
            return []
        ids = {r["asset_id"] for r in rows}
        lo = datetime.fromisoformat(rows[0]["taken_at"]) - timedelta(days=1)
        hi = datetime.fromisoformat(rows[-1]["taken_at"]) + timedelta(days=1)
        found = self.immich.search_assets(
            taken_after=lo.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            taken_before=hi.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            asset_type=asset_type,
        )
        return [a for a in found if a["id"] in ids and not a.get("is_trashed")]

    def _source(self, asset: dict, event_id: int) -> Path:
        local = self.immich.local_original(asset)
        if local:
            return local
        suffix = Path(asset.get("original_name") or "clip.mp4").suffix or ".mp4"
        dest = self.work(event_id, "originals") / f"{asset['id']}{suffix}"
        if not dest.exists():
            self.immich.download_original(asset["id"], dest)
        return dest

    def _video_sheets(self, event_id: int, assets: list[dict], progress: Progress,
                      start_ref: int = 1, lo: float = 0.1, hi: float = 0.6):
        sheets = []
        for n, a in enumerate(assets):
            progress(lo + (hi - lo) * n / max(1, len(assets)),
                     f"Looking through video {n + 1} of {len(assets)}")
            src = self._source(a, event_id)
            duration = (a.get("duration_ms") or 0) / 1000 or media.probe(self.s.ffprobe, src)["duration"]
            ref = f"V{start_ref + n}"
            img, _ = media.video_sheet(self.s.ffmpeg, src, ref, duration)
            sheets.append(picker.SheetVideo(ref, a["id"], duration, media.jpeg_bytes(img)))
        return sheets

    def _photo_sheets(self, assets: list[dict], progress: Progress, start_ref: int = 1):
        sheets = []
        for i in range(0, len(assets), 20):
            chunk = assets[i:i + 20]
            progress(0.62, f"Looking through photos {i + 1}–{i + len(chunk)} of {len(assets)}")
            items, refs = [], []
            for j, a in enumerate(chunk):
                ref = f"P{start_ref + i + j}"
                data, _ = self.immich.thumbnail(a["id"], "thumbnail")
                items.append((data, ref))
                refs.append((ref, a["id"]))
            sheets.append(picker.SheetPhotos(refs, media.jpeg_bytes(media.photo_sheet(items))))
        return sheets

    def pick(self, event_id: int, progress: Progress) -> None:
        ev = db.get_event(event_id)
        if self.claude is None:
            raise RuntimeError("Add CLAUDE_CODE_OAUTH_TOKEN to the settings file so Claude can pick")
        live = self._live_assets(event_id)
        videos = [a for a in live if a["type"] == "VIDEO" and (a.get("duration_ms") or 0) >= 1500]
        photos = [a for a in live if a["type"] == "IMAGE"]
        if not videos and not photos:
            raise RuntimeError("Nothing left in Immich for this event")
        vsheets = self._video_sheets(event_id, videos, progress)
        psheets = self._photo_sheets(photos, progress)
        target = picker.target_seconds(ev["video_seconds"], len(photos))
        total_items = len(vsheets) + len(psheets)
        clips, chosen = [], []
        for vb, pb in picker.batches(vsheets, psheets):
            share = (len(vb) + len(pb)) / max(1, total_items)
            progress(0.7, "Claude is choosing the best moments")
            content = picker.build_content(ev["title"], max(20, round(target * share)), vb, pb)
            result = picker.ask_claude(self.claude, self.s.model, content)
            c, p = picker.resolve(result, vb, pb)
            clips += c
            chosen += p
        if not clips and not chosen:
            raise RuntimeError("Claude didn't pick anything usable")
        by_id = {a["id"]: a for a in live}
        rows_out = [
            {**c, "kind": "clip", "taken_at": by_id[c["asset_id"]]["taken_at"]} for c in clips
        ] + [
            {"asset_id": p["asset_id"], "kind": "photo", "duration_s": media.PHOTO_SECONDS,
             "taken_at": by_id[p["asset_id"]]["taken_at"], "why": p["why"]} for p in chosen
        ]
        db.replace_picks(event_id, rows_out)
        progress(0.9, "Making the review album in Immich")
        album_ids = list(dict.fromkeys(r["asset_id"] for r in rows_out))
        name = ALBUM_PREFIX + ev["title"]
        description = ("Picked by Highlights. Remove anything you don't want in the video, or "
                       "add more, then tap Render in Highlights.")
        if ev["album_id"] and self.immich.album(ev["album_id"]):
            current = {a["id"] for a in self.immich.album_assets(ev["album_id"])}
            self.immich.add_to_album(ev["album_id"], [i for i in album_ids if i not in current])
            album_id = ev["album_id"]
        else:
            album_id = self.immich.create_album(name, album_ids, description)
        db.update_event(event_id, album_id=album_id)
        seconds = sum(r["duration_s"] for r in rows_out)
        db.log(f"Picked {len(clips)} clips and {len(chosen)} photos (about {seconds / 60:.1f} min)",
               event_id)

    # --- render ---------------------------------------------------------------------------

    def reconcile(self, event_id: int, progress: Progress) -> list[dict]:
        """Bring picks in line with the Immich album: drop what was removed, add what was added."""
        ev = db.get_event(event_id)
        current = [dict(r) for r in db.picks(event_id)]
        if not ev["album_id"] or not self.immich.album(ev["album_id"]):
            return current
        album = {a["id"]: a for a in self.immich.album_assets(ev["album_id"])
                 if a["id"] != ev["highlight_asset_id"]}
        kept = [p for p in current if p["asset_id"] in album]
        known = {p["asset_id"] for p in kept}
        added = [a for i, a in album.items() if i not in known]
        added_videos = [a for a in added if a["type"] == "VIDEO"]
        added_photos = [a for a in added if a["type"] == "IMAGE"]
        new_rows = [{"asset_id": a["id"], "kind": "photo", "start_s": 0,
                     "duration_s": media.PHOTO_SECONDS, "taken_at": a["taken_at"],
                     "why": "Added in Immich", "source": "added"} for a in added_photos]
        if added_videos:
            new_rows += self._clips_for_added(event_id, ev["title"], added_videos, progress)
        removed = len(current) - len(kept)
        if removed or new_rows:
            db.replace_picks(event_id, kept + new_rows)
            db.log(f"Synced with the Immich album: {removed} removed, {len(new_rows)} added",
                   event_id)
        return [dict(r) for r in db.picks(event_id)]

    def _clips_for_added(self, event_id, title, videos, progress) -> list[dict]:
        """Pick the best part of each video added in Immich. Without Claude, take the middle."""
        sheets = self._video_sheets(event_id, videos, progress, start_ref=900, lo=0.05, hi=0.15)
        rows = []
        clips = []
        if self.claude:
            try:
                extra = ("These videos were added by hand, so each must get at least one clip. "
                         "Return no photos.")
                content = picker.build_content(title, 6 * len(sheets), sheets, [], extra)
                clips, _ = picker.resolve(picker.ask_claude(self.claude, self.s.model, content),
                                          sheets, [])
            except Exception as e:
                db.log(f"Claude couldn't place the added videos ({e}); using their middles",
                       event_id)
        covered = {c["asset_id"] for c in clips}
        for s in sheets:
            if s.asset_id not in covered:
                dur = min(6.0, s.duration)
                clips.append({"asset_id": s.asset_id, "start_s": max(0, s.duration / 2 - dur / 2),
                              "duration_s": dur, "why": "Added in Immich"})
        by_id = {v["id"]: v for v in videos}
        for c in clips:
            rows.append({**c, "kind": "clip", "taken_at": by_id[c["asset_id"]]["taken_at"],
                         "source": "added"})
        return rows

    def render(self, event_id: int, progress: Progress) -> None:
        ev = db.get_event(event_id)
        rows = self.reconcile(event_id, progress)
        if not rows:
            raise RuntimeError("The album is empty; add some photos or clips in Immich first")
        seg_dir = self.work(event_id, "segments")
        for old in seg_dir.glob("*.mp4"):
            old.unlink()
        photo_dir = self.work(event_id, "photos")
        parts = []
        probes: dict[str, dict] = {}
        for n, r in enumerate(rows, 1):
            progress(0.2 + 0.65 * (n - 1) / len(rows), f"Rendering shot {n} of {len(rows)}")
            if r["kind"] == "photo":
                img = photo_dir / f"{r['asset_id']}.jpg"
                if not img.exists():
                    data, _ = self.immich.thumbnail(r["asset_id"], "preview")
                    img.write_bytes(data)
                seg = media.Segment("photo", img, 0, r["duration_s"])
            else:
                asset = self.immich.asset(r["asset_id"])
                src = self._source(asset, event_id)
                if r["asset_id"] not in probes:
                    probes[r["asset_id"]] = media.probe(self.s.ffprobe, src)
                info = probes[r["asset_id"]]
                seg = media.Segment("clip", src, r["start_s"], r["duration_s"],
                                    info["has_audio"], info["hdr"])
            out = seg_dir / f"{n:04d}.mp4"
            media.run(media.segment_command(self.s.ffmpeg, seg, out, self.encoder,
                                            self.s.qsv_device))
            parts.append(out)
        progress(0.88, "Joining the shots")
        safe = "".join(ch for ch in ev["title"] if ch.isalnum() or ch in " -,·").strip()
        final = self.work(event_id) / f"{safe or 'Highlight'}.mp4"
        media.concat(self.s.ffmpeg, parts, final)
        info = media.probe(self.s.ffprobe, final)
        progress(0.93, "Uploading to Immich")
        start = datetime.fromisoformat(ev["start_at"])
        asset_id = self.immich.upload(final, start, f"Highlight - {safe}.mp4")
        if ev["album_id"]:
            self.immich.add_to_album(ev["album_id"], [asset_id])
        hl_album = self.immich.find_album(HIGHLIGHTS_ALBUM)
        if hl_album:
            self.immich.add_to_album(hl_album["id"], [asset_id])
        else:
            self.immich.create_album(HIGHLIGHTS_ALBUM, [asset_id],
                                     "Every finished highlight video, newest first.")
        old = ev["highlight_asset_id"]
        if old and old != asset_id:
            self.immich.trash([old])  # a re-render replaces the previous version
        db.update_event(event_id, highlight_asset_id=asset_id, highlight_path=self.s.to_stored(final),
                        highlight_seconds=info["duration"], highlight_bytes=final.stat().st_size)
        shutil.rmtree(seg_dir, ignore_errors=True)
        shutil.rmtree(photo_dir, ignore_errors=True)
        db.log(f"Rendered {info['duration'] / 60:.1f} min, {final.stat().st_size / 1e6:.0f} MB, "
               f"with {self.encoder}", event_id)

    # --- cleanup --------------------------------------------------------------------------

    def cleanup_candidates(self, event_id: int) -> list[dict]:
        """Raw videos for the event that are safe to send to Immich's trash.

        Kept: favorites, the highlight itself, anything already gone, and clips the user put in
        some other album.
        """
        ev = db.get_event(event_id)
        live = {a["id"]: a for a in self._live_assets(event_id, "VIDEO")}
        if not live:
            return []
        protected: set[str] = set()
        for album in self.immich.albums():
            if album["id"] == ev["album_id"] or album.get("albumName") == HIGHLIGHTS_ALBUM:
                continue
            if album.get("assetCount", 1):
                protected |= {a["id"] for a in self.immich.album_assets(album["id"])}
        return [a for i, a in live.items()
                if i != ev["highlight_asset_id"] and not a.get("is_favorite") and i not in protected]

    def cleanup(self, event_id: int, progress: Progress) -> None:
        if not self.s.cleanup_enabled:
            raise RuntimeError("Cleanup is turned off until the Immich backup is set up")
        progress(0.2, "Checking which clips are safe to remove")
        doomed = self.cleanup_candidates(event_id)
        freed = sum(a.get("size_bytes") or 0 for a in doomed)
        progress(0.6, f"Moving {len(doomed)} clips to Immich's trash")
        for i in range(0, len(doomed), 200):
            self.immich.trash([a["id"] for a in doomed[i:i + 200]])
        db.update_event(event_id, freed_bytes=freed)
        shutil.rmtree(self.work(event_id, "originals"), ignore_errors=True)
        db.log(f"Moved {len(doomed)} raw clips ({freed / 1e9:.1f} GB) to Immich's trash. "
               "Immich deletes them for good after 30 days.", event_id)
