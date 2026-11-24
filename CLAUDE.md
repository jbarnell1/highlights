# CLAUDE.md: Highlights

Turns trips and months in an Immich library into highlight videos. Immich is where photos live
and where picks are edited and videos are watched; this app is a small phone PWA for following
the pipeline and pressing the buttons that move it. Public repo, AGPL-3.0: never commit a real
hostname, address, path, API key, token or anything about the household that runs it.

## Shape
- `config.py` settings from the environment or an env file (`HL_ENV_FILE`, default
  `~/.highlights.env`; in the container, compose's `.env`).
- `events.py` finds trips and months (pure, tested). `picker.py` asks Claude Code for picks.
  `media.py` contact sheets and ffmpeg commands. `pipeline.py` the steps. `worker.py` one
  background thread that runs queued jobs in order (one render at a time). `web.py` + templates
  the PWA.
- Paths written to the database are relative to the data folder (`Settings.to_stored`), and old
  absolute ones are re-rooted on read (`Settings.from_stored`), so the data folder can move.

## Rules
1. **Raw clips are only ever moved to Immich's trash** (`force: false`), never hard-deleted, and
   only when `HL_CLEANUP_ENABLED=true`. Favorites and clips in any other album are never trashed.
   Photos are never trashed.
2. All SQL lives in `db.py`; all Immich calls go through `immich.py` (`FakeImmich` for tests).
3. Claude Code runs with a subscription token (`CLAUDE_CODE_OAUTH_TOKEN`), never the paid API: the
   subprocess drops `ANTHROPIC_API_KEY`. Don't add `--bare`; it ignores OAuth tokens. Only the Read
   tool is allowed, inside a temporary folder of contact sheets.
4. Every segment is rendered as SDR BT.709 limited range (see `media.py`): the final join copies
   segments, and one HDR or full-range segment turns the rest of the video black in players.
5. Encoders: `detect_encoder` tries NVENC, then Quick Sync (`HL_QSV_DEVICE`), then libx264.
   `NO_WINDOW` must stay 0 outside Windows (any other value makes subprocess raise).
6. Every in-app URL is built from `base` (templates) or `request.scope["root_path"]`; the app is
   served under `HL_BASE_PATH`.
7. Tests ship with changes: `uv run pytest -q` and `uv run ruff check .`. No network in tests.
8. Mobile first: actions sit in the bottom bar, touch targets are at least 44 px, check at 375 px.
9. No em dashes in UI copy, docs, or commits.
10. Screenshots and the social preview use demo data only, never a real library. How the demo
    was made and the photo credits are in `docs/screenshots/CREDITS.md`; the logo is in
    `docs/brand/`.

## Releasing
CI (`ci.yml`) runs lint, tests and a Docker build on every push; `gitleaks.yml` scans history.
A `v*` tag publishes `ghcr.io/jbarnell1/highlights:<version>` and `:latest`
(`publish-image.yml`).

The project is in maintenance (see `docs/ROADMAP.md`): fixes, not features. To release: set the
version in `pyproject.toml` and run `uv lock`, add the section to `CHANGELOG.md`, update the
"Works today" heading in the roadmap, merge, tag `v<version>` on main, then make a GitHub release
from the tag with that changelog section as its notes.
