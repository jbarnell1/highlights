"""ffmpeg and Pillow work: contact sheets for picking, and segment rendering for the final video."""

from __future__ import annotations

import io
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

W, H, FPS = 1920, 1080, 30
PHOTO_SECONDS = 3.5
FADE = 0.3
# Keeps ffmpeg from flashing console windows on Windows. Elsewhere it must be 0: any other value
# makes subprocess raise on Linux and macOS.
NO_WINDOW = 0x08000000 if os.name == "nt" else 0
HDR_TRANSFERS = {"arib-std-b67", "smpte2084"}  # HLG and PQ, what phones record HDR video in
DEFAULT_QSV_DEVICE = "/dev/dri/renderD128"


def run(cmd: list[str], timeout: int = 1800) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                          creationflags=NO_WINDOW)
    if proc.returncode != 0:
        tail = (proc.stderr or "").strip().splitlines()[-6:]
        raise RuntimeError(f"{Path(cmd[0]).name} failed: " + " | ".join(tail))
    return proc


def probe(ffprobe: str, path: Path) -> dict:
    out = run([ffprobe, "-v", "error", "-print_format", "json", "-show_format", "-show_streams",
               str(path)], timeout=120).stdout
    data = json.loads(out)
    video = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
    audio = any(s.get("codec_type") == "audio" for s in data.get("streams", []))
    return {
        "duration": float(data.get("format", {}).get("duration") or 0),
        "width": video.get("width"),
        "height": video.get("height"),
        "has_audio": audio,
        "hdr": video.get("color_transfer") in HDR_TRANSFERS,
    }


def detect_encoder(ffmpeg: str, qsv_device: str = DEFAULT_QSV_DEVICE) -> str:
    """The first hardware encoder that works: NVIDIA (h264_nvenc), then Intel Quick Sync
    (h264_qsv). libx264 on the CPU when neither does."""
    probe_input = ["-f", "lavfi", "-i", "testsrc=d=0.5:s=640x360"]
    for encoder in ("h264_nvenc", "h264_qsv"):
        if encoder == "h264_qsv" and not Path(qsv_device).exists():
            continue
        try:
            run([ffmpeg, "-v", "error", *hw_args(encoder, qsv_device), *probe_input,
                 *encoder_args(encoder), "-f", "null", "-"], timeout=60)
            return encoder
        except Exception:  # noqa: BLE001 - any failure means "not this one"
            continue
    return "libx264"


def hw_args(encoder: str, qsv_device: str = DEFAULT_QSV_DEVICE) -> list[str]:
    """Global options that go before the inputs. Quick Sync needs to be told which GPU to use."""
    if encoder == "h264_qsv":
        return ["-init_hw_device", f"qsv=hw:{qsv_device}"]
    return []


def encoder_args(encoder: str) -> list[str]:
    """Video codec options, pixel format included: Quick Sync takes nv12, the others yuv420p."""
    if encoder == "h264_nvenc":
        return ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "21",
                "-b:v", "12M", "-maxrate", "16M", "-bufsize", "24M", "-profile:v", "high",
                "-pix_fmt", "yuv420p"]
    if encoder == "h264_qsv":
        # Low-power mode is the encoder recent Intel iGPUs have (and the only one on some).
        return ["-c:v", "h264_qsv", "-low_power", "1", "-preset", "medium",
                "-global_quality", "21", "-maxrate", "16M", "-bufsize", "24M",
                "-profile:v", "high", "-pix_fmt", "nv12"]
    return ["-c:v", "libx264", "-preset", "faster", "-crf", "21", "-maxrate", "14M",
            "-bufsize", "28M", "-pix_fmt", "yuv420p"]


# --- contact sheets ---------------------------------------------------------------------------


def _font(size: int) -> ImageFont.ImageFont:
    for name in ("segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def sample_times(duration: float, max_frames: int = 24) -> list[float]:
    """Evenly spaced frame times, one per ~4 seconds, between 6 and max_frames."""
    if duration <= 0:
        return [0.0]
    n = max(6, min(max_frames, round(duration / 4)))
    step = duration / n
    return [round(step * (i + 0.5), 2) for i in range(n)]


def extract_frame(ffmpeg: str, src: Path, t: float, width: int = 360) -> Image.Image:
    proc = subprocess.run(
        [ffmpeg, "-v", "error", "-ss", f"{t:.2f}", "-i", str(src), "-frames:v", "1",
         "-vf", f"scale={width}:-2", "-f", "image2pipe", "-vcodec", "mjpeg", "-"],
        capture_output=True, timeout=120, creationflags=NO_WINDOW,
    )
    if proc.returncode != 0 or not proc.stdout:
        return Image.new("RGB", (width, width * 9 // 16), (30, 30, 30))
    return Image.open(io.BytesIO(proc.stdout)).convert("RGB")


def tile_sheet(tiles: list[tuple[Image.Image, str]], columns: int, tile_w: int) -> Image.Image:
    """Lay labeled tiles out in a grid. Each label sits on a dark bar under its tile."""
    font = _font(20)
    bar = 30
    fitted = []
    for img, label in tiles:
        img = ImageOps.contain(img, (tile_w, tile_w))
        fitted.append((img, label))
    tile_h = max(img.height for img, _ in fitted)
    rows = (len(fitted) + columns - 1) // columns
    gap = 6
    sheet = Image.new("RGB", (columns * (tile_w + gap) + gap, rows * (tile_h + bar + gap) + gap),
                      (12, 12, 12))
    draw = ImageDraw.Draw(sheet)
    for i, (img, label) in enumerate(fitted):
        r, c = divmod(i, columns)
        x = gap + c * (tile_w + gap)
        y = gap + r * (tile_h + bar + gap)
        sheet.paste(img, (x + (tile_w - img.width) // 2, y + (tile_h - img.height) // 2))
        draw.rectangle([x, y + tile_h, x + tile_w, y + tile_h + bar], fill=(0, 0, 0))
        draw.text((x + 8, y + tile_h + 4), label, fill=(255, 230, 120), font=font)
    return sheet


def fmt_clock(t: float) -> str:
    m, s = divmod(int(round(t)), 60)
    return f"{m}:{s:02d}"


def video_sheet(ffmpeg: str, src: Path, ref: str, duration: float) -> tuple[Image.Image, list[float]]:
    times = sample_times(duration)
    tiles = [(extract_frame(ffmpeg, src, t), f"{ref} @ {fmt_clock(t)}") for t in times]
    return tile_sheet(tiles, columns=4, tile_w=360), times


def photo_sheet(items: list[tuple[bytes, str]]) -> Image.Image:
    tiles = []
    for data, ref in items:
        try:
            img = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
        except Exception:
            img = Image.new("RGB", (280, 210), (30, 30, 30))
        tiles.append((img, ref))
    return tile_sheet(tiles, columns=5, tile_w=280)


def jpeg_bytes(img: Image.Image, quality: int = 80) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality)
    return buf.getvalue()


# --- rendering --------------------------------------------------------------------------------


@dataclass
class Segment:
    kind: str  # "clip" | "photo"
    source: Path
    start: float
    duration: float
    has_audio: bool = False
    hdr: bool = False


# Every segment must come out as the same SDR BT.709 limited-range stream: the final join copies
# the segments as they are, and a player that meets an HDR or full-range segment after an SDR one
# shows black. HDR phone clips are tone mapped; JPEG photos are full range and get squeezed.
# Shrink 4K first (nothing is shown larger than 1920) so the float tone mapping stays quick.
_TONEMAP = ("scale='min(1920,iw)':'min(1920,ih)':force_original_aspect_ratio=decrease:"
            "force_divisible_by=2,zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,"
            "tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p")
_TO_SDR = "scale=out_range=tv:out_color_matrix=bt709,format=yuv420p"
_TAGS = "setparams=range=tv:color_primaries=bt709:color_trc=bt709:colorspace=bt709"
_TAG_ARGS = ["-color_range", "tv", "-color_primaries", "bt709", "-color_trc", "bt709",
             "-colorspace", "bt709"]


def _compose(hdr: bool) -> str:
    """Fill the frame with a blurred copy of the shot, then fit the shot itself on top, so
    portrait phone clips and photos don't get black bars."""
    return (
        f"[0:v]{_TONEMAP if hdr else _TO_SDR},split=2[a][b];"
        f"[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=24:4,"
        "eq=brightness=-0.08[bg];"
        f"[b]scale={W}:{H}:force_original_aspect_ratio=decrease[fg];"
        "[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1"
    )


def segment_command(ffmpeg: str, seg: Segment, out: Path, encoder: str,
                    qsv_device: str = DEFAULT_QSV_DEVICE) -> list[str]:
    d = seg.duration
    fade_out = max(0.0, d - FADE)
    fades = f"fade=t=in:st=0:d={FADE},fade=t=out:st={fade_out:.2f}:d={FADE}"
    afades = f"afade=t=in:st=0:d={FADE},afade=t=out:st={fade_out:.2f}:d={FADE}"
    ffmpeg_hw = [ffmpeg, *hw_args(encoder, qsv_device)]
    common_out = [*encoder_args(encoder), *_TAG_ARGS, "-r", str(FPS),
                  "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
                  "-video_track_timescale", "30000", "-movflags", "+faststart", str(out)]
    if seg.kind == "photo":
        frames = int(round(d * FPS))
        # Slow push-in. Upscale first so the zoom doesn't shimmer.
        vf = (
            f"{_compose(False)},scale={W * 2}:{H * 2},"
            f"zoompan=z='min(zoom+0.0009,1.12)':d={frames}:x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},format=yuv420p,{_TAGS},{fades}[v]"
        )
        return [*ffmpeg_hw, "-v", "error", "-y", "-i", str(seg.source),
                "-f", "lavfi", "-t", f"{d:.2f}", "-i", "anullsrc=r=48000:cl=stereo",
                "-filter_complex", vf, "-map", "[v]", "-map", "1:a", "-t", f"{d:.2f}", *common_out]
    vf = f"{_compose(seg.hdr)},fps={FPS},format=yuv420p,{_TAGS},{fades}[v]"
    cmd = [*ffmpeg_hw, "-v", "error", "-y", "-ss", f"{seg.start:.2f}", "-t", f"{d:.2f}",
           "-i", str(seg.source)]
    if seg.has_audio:
        af = f"[0:a]aresample=48000,aformat=channel_layouts=stereo,{afades}[a]"
        return [*cmd, "-filter_complex", f"{vf};{af}", "-map", "[v]", "-map", "[a]", *common_out]
    return [*cmd, "-f", "lavfi", "-t", f"{d:.2f}", "-i", "anullsrc=r=48000:cl=stereo",
            "-filter_complex", vf, "-map", "[v]", "-map", "1:a", "-shortest", *common_out]


def concat(ffmpeg: str, parts: list[Path], out: Path) -> None:
    listing = out.with_suffix(".txt")
    listing.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="ascii")
    run([ffmpeg, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
         "-c", "copy", "-movflags", "+faststart", str(out)])
    listing.unlink(missing_ok=True)
