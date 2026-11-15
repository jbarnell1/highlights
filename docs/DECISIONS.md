# Decisions

Newest first.

### D-007 Claude Code is confined to the contact sheets, enforced
**2026-11-14.** D-004 said the picking subprocess "sees only a temporary folder", but that rested
on its working directory and the prompt: `--allowedTools Read` with no path let it read any file
the process could, including the photo library mounted in the container, and it inherited every
environment variable, the Immich API key among them. Now the allow rule is `Read(./**)` with the
temp folder as the working directory (tested against the real CLI: a read outside is denied),
Glob and Grep are off with the other tools, and the subprocess environment drops `IMMICH_*`,
`HL_*`, `ANTHROPIC_*` and anything named like a key, token, secret or password. Supersedes the
confinement part of D-004.

### D-006 Linux and Intel Quick Sync, packaged as a container
**2026-11-14.** Highlights moved from a Windows PC with an NVIDIA GTX 1060 to a Linux server with
an Intel iGPU. It now ships as a Docker image with Jellyfin's ffmpeg build (Quick Sync, the Intel
media driver, zscale and tonemap in one package) and the Claude Code CLI. Encoder order: NVENC,
Quick Sync, libx264. Quick Sync takes nv12 and runs in low-power mode, which recent Intel iGPUs
support (and some only support). Paths in the database became relative to the data folder so it
could move between machines. Rejected: Debian's ffmpeg (no oneVPL Quick Sync in the stable build)
and a host install with a systemd unit (the household's other apps all run as containers).

### D-005 Every segment is SDR BT.709
**2026-11.** The final join copies segments as they are. One HDR or full-range segment made
players show black from that point on, so HDR phone clips are tone mapped (hable) and JPEG photos
are squeezed to limited range before encoding.

### D-004 Picks through Claude Code on a subscription
**2026-11.** Picking runs the Claude Code CLI in print mode with `--json-schema`, signed in with a
subscription token from `claude setup-token`, so it counts against the plan instead of an API
bill. The subprocess drops `ANTHROPIC_API_KEY`, allows only the Read tool, and sees only a
temporary folder of contact sheets. Rejected: the Messages API directly (separate billing).

### D-003 Contact sheets, not uploads
**2026-11.** Claude sees labeled grids of frames (one sheet per video, frames spaced evenly with
their times) and grids of photo thumbnails, never the original files. It answers with refs and
times, which are clamped to the real video lengths.

### D-002 Immich is the editor
**2026-11.** Picks become an Immich album and Render reconciles with that album first, so any
edit made in Immich wins. The app itself stays a small status-and-buttons PWA.

### D-001 Clips go to the trash, never deleted
**2026-11.** Cleanup only moves raw clips to Immich's trash (`force: false`, recoverable for 30
days), only when `HL_CLEANUP_ENABLED=true`, and never touches favorites, photos, or clips in any
other album. It stays off until the library has an offsite backup.
