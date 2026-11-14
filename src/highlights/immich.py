"""The only code that talks to Immich. FakeImmich mirrors it for tests."""

from __future__ import annotations

import mimetypes
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import httpx


def normalize(raw: dict) -> dict:
    """Flatten an Immich AssetResponseDto into the fields the pipeline uses."""
    exif = raw.get("exifInfo") or {}
    # localDateTime is wall-clock time at the place the photo was taken, written with a "Z".
    local = (raw.get("localDateTime") or raw.get("fileCreatedAt") or "").replace("Z", "")
    return {
        "id": raw["id"],
        "type": raw.get("type", "IMAGE"),
        "taken_at": local[:19],
        "lat": exif.get("latitude"),
        "lon": exif.get("longitude"),
        "city": exif.get("city"),
        "state": exif.get("state"),
        "country": exif.get("country"),
        "duration_ms": raw.get("duration"),
        "size_bytes": exif.get("fileSizeInByte"),
        "is_favorite": bool(raw.get("isFavorite")),
        "is_trashed": bool(raw.get("isTrashed")),
        "original_path": raw.get("originalPath"),
        "original_name": raw.get("originalFileName"),
        "mime": raw.get("originalMimeType"),
        "width": raw.get("width") or exif.get("exifImageWidth"),
        "height": raw.get("height") or exif.get("exifImageHeight"),
    }


class ImmichError(RuntimeError):
    pass


class Immich:
    def __init__(self, base_url: str, api_key: str, media_root: Path | None = None):
        self.base = base_url.rstrip("/") + "/api"
        self.media_root = media_root
        self.http = httpx.Client(
            headers={"x-api-key": api_key, "Accept": "application/json"},
            timeout=httpx.Timeout(60, connect=10),
        )

    def _check(self, r: httpx.Response) -> httpx.Response:
        if r.status_code >= 400:
            raise ImmichError(f"Immich {r.request.method} {r.request.url.path}: "
                              f"{r.status_code} {r.text[:300]}")
        return r

    def me(self) -> dict:
        return self._check(self.http.get(f"{self.base}/users/me")).json()

    def search_assets(
        self,
        taken_after: str | None = None,
        taken_before: str | None = None,
        album_id: str | None = None,
        asset_type: str | None = None,
    ) -> Iterator[dict]:
        body: dict = {"withExif": True, "size": 1000, "order": "asc"}
        if taken_after:
            body["takenAfter"] = taken_after
        if taken_before:
            body["takenBefore"] = taken_before
        if album_id:
            body["albumIds"] = [album_id]
        if asset_type:
            body["type"] = asset_type
        page: str | None = None
        while True:
            req = dict(body)
            if page:
                if page.isdigit():
                    req["page"] = int(page)
                else:
                    req["cursor"] = page
            data = self._check(self.http.post(f"{self.base}/search/metadata", json=req)).json()
            assets = data.get("assets") or {}
            for item in assets.get("items", []):
                yield normalize(item)
            page = assets.get("nextPage")
            if not page:
                return

    def asset(self, asset_id: str) -> dict:
        return normalize(self._check(self.http.get(f"{self.base}/assets/{asset_id}")).json())

    def thumbnail(self, asset_id: str, size: str = "thumbnail") -> tuple[bytes, str]:
        r = self._check(self.http.get(f"{self.base}/assets/{asset_id}/thumbnail",
                                      params={"size": size}))
        return r.content, r.headers.get("content-type", "image/jpeg")

    def local_original(self, asset: dict) -> Path | None:
        """The original file on this machine's disk, if Immich keeps it under the media root."""
        path = asset.get("original_path") or ""
        if self.media_root and path.startswith("/data/"):
            local = self.media_root / Path(path[len("/data/"):])
            if local.exists():
                return local
        return None

    def download_original(self, asset_id: str, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with self.http.stream("GET", f"{self.base}/assets/{asset_id}/original",
                              timeout=httpx.Timeout(600, connect=10)) as r:
            self._check(r)
            with open(dest, "wb") as f:
                for chunk in r.iter_bytes(1 << 20):
                    f.write(chunk)
        return dest

    # --- albums ---

    def albums(self) -> list[dict]:
        return self._check(self.http.get(f"{self.base}/albums")).json()

    def album(self, album_id: str) -> dict | None:
        r = self.http.get(f"{self.base}/albums/{album_id}")
        if r.status_code in (400, 404):
            return None
        return self._check(r).json()

    def find_album(self, name: str) -> dict | None:
        return next((a for a in self.albums() if a.get("albumName") == name), None)

    def create_album(self, name: str, asset_ids: list[str], description: str = "") -> str:
        r = self._check(self.http.post(f"{self.base}/albums", json={
            "albumName": name, "description": description, "assetIds": asset_ids,
        }))
        return r.json()["id"]

    def album_assets(self, album_id: str) -> list[dict]:
        return list(self.search_assets(album_id=album_id))

    def add_to_album(self, album_id: str, asset_ids: list[str]) -> None:
        if asset_ids:
            self._check(self.http.put(f"{self.base}/albums/{album_id}/assets",
                                      json={"ids": asset_ids}))

    def rename_album(self, album_id: str, name: str, description: str | None = None) -> None:
        body: dict = {"albumName": name}
        if description is not None:
            body["description"] = description
        self._check(self.http.patch(f"{self.base}/albums/{album_id}", json=body))

    # --- writes ---

    def upload(self, path: Path, created_at: datetime, filename: str) -> str:
        stamp = created_at.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        mime = mimetypes.guess_type(filename)[0] or "video/mp4"
        with open(path, "rb") as f:
            r = self._check(self.http.post(
                f"{self.base}/assets",
                data={"fileCreatedAt": stamp, "fileModifiedAt": stamp, "filename": filename},
                files={"assetData": (filename, f, mime)},
                timeout=httpx.Timeout(1800, connect=10),
            ))
        return r.json()["id"]

    def trash(self, asset_ids: list[str]) -> None:
        """Move to Immich's trash (recoverable for 30 days). Never a permanent delete."""
        if asset_ids:
            self._check(self.http.request("DELETE", f"{self.base}/assets",
                                          json={"ids": asset_ids, "force": False}))


class FakeImmich:
    """In-memory stand-in with the same surface, for tests."""

    def __init__(self, assets: list[dict] | None = None):
        self.assets = {a["id"]: a for a in (assets or [])}
        self.album_data: dict[str, dict] = {}
        self.album_members: dict[str, list[str]] = {}
        self.uploaded: list[tuple[Path, str]] = []
        self.trashed: list[str] = []
        self.media_root = None

    def me(self) -> dict:
        return {"name": "Test"}

    def search_assets(self, taken_after=None, taken_before=None, album_id=None, asset_type=None):
        items = sorted(self.assets.values(), key=lambda a: a["taken_at"])
        if album_id:
            members = set(self.album_members.get(album_id, []))
            items = [a for a in items if a["id"] in members]
        for a in items:
            if asset_type and a["type"] != asset_type:
                continue
            if a["id"] in self.trashed:
                continue
            yield a

    def asset(self, asset_id):
        return self.assets[asset_id]

    def thumbnail(self, asset_id, size="thumbnail"):
        return b"", "image/jpeg"

    def local_original(self, asset):
        return None

    def download_original(self, asset_id, dest):
        raise ImmichError("fake has no files")

    def albums(self):
        return list(self.album_data.values())

    def album(self, album_id):
        return self.album_data.get(album_id)

    def find_album(self, name):
        return next((a for a in self.album_data.values() if a["albumName"] == name), None)

    def create_album(self, name, asset_ids, description=""):
        album_id = f"album-{len(self.album_data) + 1}"
        self.album_data[album_id] = {"id": album_id, "albumName": name, "description": description}
        self.album_members[album_id] = list(asset_ids)
        return album_id

    def album_assets(self, album_id):
        return list(self.search_assets(album_id=album_id))

    def add_to_album(self, album_id, asset_ids):
        members = self.album_members.setdefault(album_id, [])
        members.extend(a for a in asset_ids if a not in members)

    def rename_album(self, album_id, name, description=None):
        self.album_data[album_id]["albumName"] = name

    def upload(self, path, created_at, filename):
        asset_id = f"upload-{len(self.uploaded) + 1}"
        self.uploaded.append((path, filename))
        self.assets[asset_id] = {"id": asset_id, "type": "VIDEO", "taken_at": created_at.isoformat(),
                                 "is_favorite": False}
        return asset_id

    def trash(self, asset_ids):
        self.trashed.extend(asset_ids)
