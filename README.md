# Highlights

Turns the trips and months in a self-hosted [Immich](https://immich.app) library into highlight
videos. Highlights finds the events, Claude picks the moments from contact sheets of every
video and photo, and ffmpeg cuts them into one video that lands back in Immich. A small phone
web app shows where each event is and has the buttons that move it along.

- **Events are found for you.** Trips are runs of photos taken far from home; everything else
  groups by month. Nothing is touched until you press a button.
- **Claude picks, you edit in Immich.** The picks become an Immich album. Add or remove shots
  there before rendering; Highlights uses whatever is in the album.
- **Renders on the GPU when there is one:** Intel Quick Sync or NVIDIA NVENC, else the CPU.
  HDR phone clips are tone mapped so the whole video plays as SDR.
- **Careful with your library.** Raw clips are only ever moved to Immich's trash, never deleted,
  and only when you turn cleanup on (after your library has an offsite backup). Favorites, photos
  and clips in other albums are never touched.

Picking uses the [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI signed in with
a Claude subscription (Pro or Max), so it counts against the plan instead of an API bill. Contact
sheets are small JPEG grids; your original photos and videos are not uploaded.

Status: used by one household. Expect rough edges. License: AGPL-3.0.

## Run it

Requirements: Docker with Compose, an Immich server, and a Claude subscription.

```bash
git clone https://github.com/jbarnell1/highlights && cd highlights
cp .env.example .env
```

In `.env`:

1. `IMMICH_API_KEY`: in Immich, your avatar > Account Settings > API Keys > New API Key.
2. `CLAUDE_CODE_OAUTH_TOKEN`: run `claude setup-token` on any computer with Claude Code, sign in,
   and paste the token.
3. `IMMICH_LIBRARY`: the folder Immich stores originals in (its `UPLOAD_LOCATION`), if Immich runs
   on the same machine. It is mounted read-only.
4. `RENDER_GID`: for Intel Quick Sync, the output of `getent group render | cut -d: -f3`.

```bash
docker compose up -d
docker compose exec highlights hl check   # settings, Immich login, encoder, Claude Code
```

The app listens on `127.0.0.1:8040` under `/highlights`. Put a reverse proxy in front, for example
`tailscale serve --bg --https=443 --set-path=/highlights http://127.0.0.1:8040`. It has no login of
its own: keep it on a private network.

`compose.yaml` joins Immich's Docker network (`immich_default`) and reaches it at
`http://immich_server:2283`. If Immich runs elsewhere, drop that network and set `IMMICH_URL`.

### Without Docker

Python 3.12, [uv](https://docs.astral.sh/uv/), ffmpeg (with zscale for HDR clips) and Claude Code
on `PATH`:

```bash
uv sync
cp .env.example ~/.highlights.env    # or set HL_ENV_FILE
uv run hl check
uv run hl serve --port 8040
```

Set `HL_DATA_DIR` for where the database and renders go, and `IMMICH_MEDIA_ROOT` to Immich's
originals folder if this machine can read it.

## How it works

`found > picking > picks_ready > rendering > ready > (cleaning) > done`, plus `dismissed`.

1. **Scan** (daily, or on demand) reads photo times and places from Immich and groups them into
   trips and months (`events.py`).
2. **Pick**: each video becomes a contact sheet of frames labeled with times; photos go into
   labeled grids. Claude Code reads the sheets and returns clip times and photo refs as JSON
   (`picker.py`). Picks become an Immich album.
3. **Render** reconciles with that album, cuts each shot (blurred fill for portrait shots, slow
   push-in on photos, HDR tone mapping), joins them and uploads the video to Immich, into the
   event's album and a "Highlights" album (`media.py`, `pipeline.py`).
4. **Clean up** (optional, off by default) moves the event's raw clips to Immich's trash.

Settings: see `.env.example`. Design notes: `docs/DECISIONS.md`.

## Development

```bash
uv sync
uv run pytest -q
uv run ruff check .
```

Tests use a fake Immich and need no network, GPU or Claude account.
