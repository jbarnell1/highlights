"""Claude picks the moments: it reads labeled contact sheets and returns clip times and photos."""

from __future__ import annotations

import base64
import json
import math
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

MIN_CLIP, MAX_CLIP = 2.0, 12.0
MAX_IMAGES_PER_REQUEST = 90


class ClipPick(BaseModel):
    ref: str = Field(description="Video label from the sheet, like V3")
    start: float = Field(description="Start time in seconds within that video")
    duration: float = Field(description="Clip length in seconds, 3 to 8 for most shots")
    why: str = Field(description="A few words on what the moment shows")


class PhotoPick(BaseModel):
    ref: str = Field(description="Photo label from the sheet, like P12")
    why: str


class Picks(BaseModel):
    clips: list[ClipPick]
    photos: list[PhotoPick]
    notes: str = Field(description="One or two sentences on the story the picks tell")


SCHEMA = {
    "type": "object",
    "properties": {
        "clips": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "ref": {"type": "string"}, "start": {"type": "number"},
                "duration": {"type": "number"}, "why": {"type": "string"},
            },
            "required": ["ref", "start", "duration", "why"], "additionalProperties": False,
        }},
        "photos": {"type": "array", "items": {
            "type": "object",
            "properties": {"ref": {"type": "string"}, "why": {"type": "string"}},
            "required": ["ref", "why"], "additionalProperties": False,
        }},
        "notes": {"type": "string"},
    },
    "required": ["clips", "photos", "notes"],
    "additionalProperties": False,
}

SYSTEM = """You edit family highlight videos from a personal photo library.

You get contact sheets. Each video has its own sheet: frames spaced evenly through the clip, each
labeled with the video's ref and the time of that frame (for example "V3 @ 1:23"). Photos come in
grids, each labeled with its ref (for example "P12").

Choose the moments that tell the story of the event, the way a thoughtful family member would
cut it:
- Favor people's faces, reactions, kids, firsts, and moments of play over empty scenery. Keep a
  few scenic shots for place and pacing, especially establishing shots near the start.
- Skip blurry, dark, accidental, pocket, or underwater-splash frames, near-duplicates, and
  screenshots or documents.
- Spread picks across the whole event so every day or chapter shows up.
- Clips: start a clip at or just before a frame that looks good and keep it 3 to 8 seconds
  (up to 12 for a payoff like fireworks or a big wave). Never run past the end of the video.
  Two clips from the same video are fine when it covers different moments.
- Photos: pick ones that add something clips don't. Each photo plays for about 3.5 seconds.
- Aim for the target length you are given, within about 15 percent.

Return only the picks. Order does not matter; the video is assembled in the order things happened.
"""


@dataclass
class SheetVideo:
    ref: str
    asset_id: str
    duration: float
    jpeg: bytes


@dataclass
class SheetPhotos:
    refs: list[tuple[str, str]]  # (ref, asset_id)
    jpeg: bytes


def target_seconds(video_seconds: float, photo_count: int) -> int:
    """About 4.5 minutes for a big trip, a minute or so for a quiet month."""
    raw = 6 * math.sqrt(max(video_seconds, 0)) + 1.2 * math.sqrt(max(photo_count, 0)) * 6
    return int(min(300, max(45, raw)))


def _image_block(jpeg: bytes) -> dict:
    return {"type": "image", "source": {
        "type": "base64", "media_type": "image/jpeg",
        "data": base64.standard_b64encode(jpeg).decode("ascii"),
    }}


def build_content(title: str, target: int, videos: list[SheetVideo],
                  photo_sheets: list[SheetPhotos], extra: str = "") -> list[dict]:
    content: list[dict] = [{"type": "text", "text": (
        f"Event: {title}\nTarget length: about {target} seconds.\n"
        f"{len(videos)} videos and {sum(len(s.refs) for s in photo_sheets)} photos follow.\n{extra}"
    )}]
    for v in videos:
        content.append({"type": "text", "text": f"{v.ref}: video, {v.duration:.0f} seconds long"})
        content.append(_image_block(v.jpeg))
    for i, sheet in enumerate(photo_sheets, 1):
        refs = ", ".join(r for r, _ in sheet.refs)
        content.append({"type": "text", "text": f"Photo sheet {i}: {refs}"})
        content.append(_image_block(sheet.jpeg))
    return content


class ClaudeCode:
    """Runs picks through the Claude Code CLI in print mode, signed in with the Max plan.

    Usage counts against the plan's limits instead of a separate API bill. The contact sheets are
    written to a folder Claude may only read; every other tool is turned off.
    """

    def __init__(self, exe: Path, token: str, model: str, work_dir: Path):
        self.exe, self.token, self.model, self.work_dir = exe, token, model, work_dir

    def ask(self, content: list[dict]) -> Picks:
        run_dir = Path(tempfile.mkdtemp(prefix="pick-", dir=self.work_dir))
        try:
            prompt = self._prompt(content, run_dir)
            env = {k: v for k, v in os.environ.items()
                   if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}  # never bill the API
            env["CLAUDE_CODE_OAUTH_TOKEN"] = self.token
            proc = subprocess.run(
                [str(self.exe), "-p", "--output-format", "json",
                 "--json-schema", json.dumps(SCHEMA), "--model", self.model,
                 "--append-system-prompt", SYSTEM,
                 "--allowedTools", "Read", "--disallowedTools", DISALLOWED,
                 "--add-dir", str(run_dir), "--no-session-persistence"],
                input=prompt, capture_output=True, text=True, encoding="utf-8",
                cwd=run_dir, env=env, timeout=45 * 60, creationflags=NO_WINDOW,
            )
        finally:
            shutil.rmtree(run_dir, ignore_errors=True)
        return parse_cli_output(proc.stdout, proc.stderr)

    @staticmethod
    def _prompt(content: list[dict], run_dir: Path) -> str:
        lines = ["Pick the moments for this highlight video. Use the Read tool to look at every "
                 "contact sheet image listed below before you answer.", ""]
        n = 0
        for block in content:
            if block["type"] == "text":
                lines.append(block["text"])
            elif block["type"] == "image":
                n += 1
                path = run_dir / f"sheet-{n:03d}.jpg"
                path.write_bytes(base64.standard_b64decode(block["source"]["data"]))
                lines.append(f"  Sheet image: {path}")
        lines += ["", "When you have looked at every sheet, answer with the picks as JSON."]
        return "\n".join(lines)


DISALLOWED = "Bash,Edit,Write,NotebookEdit,WebFetch,WebSearch,Task,Agent"
NO_WINDOW = 0x08000000 if os.name == "nt" else 0  # nonzero raises outside Windows


def parse_cli_output(stdout: str, stderr: str = "") -> Picks:
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as e:
        tail = (stderr or stdout or "").strip()[-300:]
        raise RuntimeError(f"Claude Code didn't answer: {tail or 'no output'}") from e
    if data.get("is_error"):
        message = str(data.get("result") or data.get("subtype") or "unknown error")
        if "log" in message.lower() and "in" in message.lower():
            message += ". Run `claude setup-token` and put the token in the settings file."
        elif "limit" in message.lower():
            message = f"Your Max plan usage limit was reached ({message}). Try again after it resets."
        raise RuntimeError(f"Claude Code: {message}")
    picks = data.get("structured_output")
    if picks is None:
        text = str(data.get("result") or "").strip()
        if text.startswith("```"):
            text = text.strip("`").removeprefix("json").strip()
        try:
            picks = json.loads(text)
        except json.JSONDecodeError as e:
            raise RuntimeError("Claude Code answered without the picks JSON") from e
    try:
        return Picks.model_validate(picks)
    except ValidationError as e:
        raise RuntimeError(f"Claude returned picks in an unexpected shape: {e}") from e


def ask_claude(runner: ClaudeCode, model: str, content: list[dict]) -> Picks:
    return runner.ask(content)


def resolve(picks: Picks, videos: list[SheetVideo],
            photo_sheets: list[SheetPhotos]) -> tuple[list[dict], list[dict]]:
    """Map refs back to asset ids and clamp clip times to the real video length."""
    by_ref = {v.ref: v for v in videos}
    photo_refs = {ref: asset_id for s in photo_sheets for ref, asset_id in s.refs}
    clips, photos, seen_photos = [], [], set()
    for c in picks.clips:
        v = by_ref.get(c.ref.strip().upper())
        if not v or v.duration <= 0:
            continue
        dur = min(max(c.duration, MIN_CLIP), MAX_CLIP, v.duration)
        start = min(max(c.start, 0.0), max(0.0, v.duration - dur))
        clips.append({"asset_id": v.asset_id, "start_s": round(start, 2),
                      "duration_s": round(dur, 2), "why": c.why})
    for p in picks.photos:
        asset_id = photo_refs.get(p.ref.strip().upper())
        if asset_id and asset_id not in seen_photos:
            seen_photos.add(asset_id)
            photos.append({"asset_id": asset_id, "why": p.why})
    return clips, photos


def batches(videos: list[SheetVideo], photo_sheets: list[SheetPhotos]):
    """Split a very large event so each request stays under the image limit."""
    items: list[SheetVideo | SheetPhotos] = [*videos, *photo_sheets]
    for i in range(0, len(items), MAX_IMAGES_PER_REQUEST):
        chunk = items[i:i + MAX_IMAGES_PER_REQUEST]
        yield ([x for x in chunk if isinstance(x, SheetVideo)],
               [x for x in chunk if isinstance(x, SheetPhotos)])
