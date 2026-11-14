"""Settings, read once from the environment and an optional env file outside the repo."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path, PureWindowsPath

ENV_FILE = Path(os.environ.get("HL_ENV_FILE", Path.home() / ".highlights.env"))


def _load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name) or _FILE_VALUES.get(name, default)


_FILE_VALUES = _load_env_file(ENV_FILE)


def _float_or_none(value: str) -> float | None:
    try:
        return float(value) if value else None
    except ValueError:
        return None


def _path_or_none(value: str) -> Path | None:
    return Path(value) if value else None


@dataclass(frozen=True)
class Settings:
    immich_url: str = field(default_factory=lambda: _get("IMMICH_URL", "http://127.0.0.1:2283"))
    # The address people open Immich at, for links from the app. Defaults to IMMICH_URL.
    immich_public_url: str = field(default_factory=lambda: _get("IMMICH_PUBLIC_URL"))
    immich_api_key: str = field(default_factory=lambda: _get("IMMICH_API_KEY"))
    # Immich keeps originals under /data inside its container. When this machine can see that
    # same folder (read-only is enough), clips are read straight off disk instead of downloaded.
    immich_media_root: Path | None = field(
        default_factory=lambda: _path_or_none(_get("IMMICH_MEDIA_ROOT"))
    )
    # Picking runs through Claude Code on a Claude subscription (claude setup-token), not the API.
    claude_token: str = field(default_factory=lambda: _get("CLAUDE_CODE_OAUTH_TOKEN"))
    claude_path: Path = field(
        default_factory=lambda: Path(_get("HL_CLAUDE") or shutil.which("claude") or "claude")
    )
    model: str = field(default_factory=lambda: _get("HL_MODEL", "opus"))
    data_dir: Path = field(default_factory=lambda: Path(_get("HL_DATA_DIR", "data")))
    # Folder holding ffmpeg and ffprobe. Empty means whatever is on PATH.
    ffmpeg_dir: Path | None = field(default_factory=lambda: _path_or_none(_get("HL_FFMPEG_DIR")))
    # Intel Quick Sync render node, used when the GPU is Intel (see media.detect_encoder).
    qsv_device: str = field(default_factory=lambda: _get("HL_QSV_DEVICE", "/dev/dri/renderD128"))
    home_lat: float | None = field(default_factory=lambda: _float_or_none(_get("HL_HOME_LAT")))
    home_lon: float | None = field(default_factory=lambda: _float_or_none(_get("HL_HOME_LON")))
    away_km: float = field(default_factory=lambda: float(_get("HL_AWAY_KM", "80")))
    # Raw clips stay put until the Immich library has an offsite backup. Flip this once it does.
    cleanup_enabled: bool = field(
        default_factory=lambda: _get("HL_CLEANUP_ENABLED", "false").lower() in ("1", "true", "yes")
    )
    base_path: str = field(default_factory=lambda: _get("HL_BASE_PATH", "/highlights"))
    # 127.0.0.1 behind a reverse proxy on the same machine; 0.0.0.0 inside a container.
    host: str = field(default_factory=lambda: _get("HL_HOST", "127.0.0.1"))

    @property
    def db_path(self) -> Path:
        return self.data_dir / "highlights.db"

    @property
    def work_dir(self) -> Path:
        return self.data_dir / "work"

    @property
    def immich_link(self) -> str:
        return (self.immich_public_url or self.immich_url).rstrip("/")

    def _tool(self, name: str) -> str:
        if self.ffmpeg_dir:
            for candidate in (name, f"{name}.exe"):
                exe = self.ffmpeg_dir / candidate
                if exe.exists():
                    return str(exe)
        return name

    @property
    def ffmpeg(self) -> str:
        return self._tool("ffmpeg")

    @property
    def ffprobe(self) -> str:
        return self._tool("ffprobe")

    def to_stored(self, path: Path) -> str:
        """How a file under the data folder is written to the database: relative, with forward
        slashes, so the data folder can move between machines and operating systems."""
        try:
            return path.relative_to(self.data_dir).as_posix()
        except ValueError:
            return str(path)

    def from_stored(self, stored: str | None) -> Path | None:
        """The local file for a stored path. Older rows hold absolute paths from wherever the data
        folder used to live (for example E:\\Highlights\\work\\...); those are re-rooted here."""
        if not stored:
            return None
        if "\\" in stored or (len(stored) > 1 and stored[1] == ":"):
            parts = PureWindowsPath(stored).parts
        else:
            parts = Path(stored).parts
        if not Path(stored).is_absolute() and not PureWindowsPath(stored).is_absolute():
            return self.data_dir.joinpath(*parts)
        if "work" in parts:
            return self.data_dir.joinpath(*parts[parts.index("work"):])
        return Path(stored)

    def missing(self) -> list[str]:
        """Settings the pipeline cannot run without, named the way the env file names them."""
        out = []
        if not self.immich_api_key:
            out.append("IMMICH_API_KEY")
        if not self.claude_token:
            out.append("CLAUDE_CODE_OAUTH_TOKEN")
        return out


settings = Settings()
