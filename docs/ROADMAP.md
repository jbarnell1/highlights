# Roadmap

Highlights is used by one household and built in spare time. This page says what works today,
what is known to be missing, and what might come next. Nothing here is a promise or a date.
The reasons behind past choices are in [DECISIONS.md](DECISIONS.md).

## Works today (0.2.0)

- Finds trips and finished months in an Immich library, daily or on demand.
- Claude picks clips and photos from contact sheets; the picks become an Immich album.
- Renders a 1080p H.264 video from whatever is in that album and uploads it to Immich.
- Encodes with NVIDIA NVENC, Intel Quick Sync, or the CPU. HDR phone clips are tone mapped.
- Optional cleanup that moves an event's raw clips to Immich's trash, off by default.
- A phone web app (installable PWA) to follow each event and press the buttons.
- A Docker image for linux/amd64 with ffmpeg and the Claude Code CLI inside.

## Known limits

- **Picking needs a Claude subscription and sends contact sheets to Anthropic.** There is no
  local-model option yet. See "What leaves your server" in the [README](../README.md).
- **No login.** The app trusts whoever can reach it. Keep it on a private network.
- **One Immich user.** It works with the library of the account that owns the API key.
- **One output format:** 1920x1080, 30 fps, H.264, landscape. Portrait shots get a blurred fill.
- **No music, titles or captions.** Clips keep their own sound; photos are silent.
- **Trip detection is simple.** A trip is 12 or more photos and videos taken more than
  `HL_AWAY_KM` from home over at least 12 hours, with no gap longer than 48 hours. Only the
  distance is a setting.
- **The image is amd64 only**, and `compose.yaml` sets up hardware encoding for Intel Quick Sync
  only. NVENC was used on the original Windows install (run without Docker); inside the
  container it would need the NVIDIA container runtime, which is not set up or tested.
- **Tested against one Immich install.** The unit tests use a fake Immich; there are no browser
  tests and no automated test against a real Immich server or the real Claude Code CLI.

## Ideas for later

Roughly in the order they seem useful. Open an issue if one matters to you.

- A local vision model as an alternative picker, so nothing has to leave the server.
- A demo mode with sample data, to try the app without Immich or a Claude account.
- Background music from a folder of your own tracks.
- Settings for the trip rules (minimum size, gap) and for output length.
- Vertical output for phones.
- An arm64 image.
