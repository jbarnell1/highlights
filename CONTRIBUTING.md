# Contributing to Highlights

Thanks for looking. Highlights is a small project run by one household, so reviews can take a few
days. Bug reports with exact steps are as welcome as code.

## Before you start

- **Bugs and small fixes:** open an issue or go straight to a pull request.
- **New features:** open an issue first and describe what you want to do. The app is kept small
  on purpose (Immich is the editor and the player, see `docs/DECISIONS.md`), so it is worth
  agreeing on the shape before you write code.
- **Security problems:** do not open a public issue. See [SECURITY.md](SECURITY.md).

## Set up

You need Python 3.12 and [uv](https://docs.astral.sh/uv/). ffmpeg, Immich, a GPU and a Claude
account are not needed to run the tests.

```bash
git clone https://github.com/jbarnell1/highlights && cd highlights
uv sync
uv run pytest -q
uv run ruff check .
```

To run the app itself, see "Without Docker" in the [README](README.md#without-docker).

## Where things live

| File | What it does |
|---|---|
| `src/highlights/config.py` | Settings from the environment or an env file |
| `src/highlights/events.py` | Finds trips and months. Pure functions, no I/O |
| `src/highlights/picker.py` | Builds the request for Claude Code and checks the answer |
| `src/highlights/media.py` | Contact sheets and ffmpeg commands |
| `src/highlights/pipeline.py` | The steps: scan, pick, render, clean up |
| `src/highlights/worker.py` | One background thread that runs queued jobs in order |
| `src/highlights/immich.py` | The only code that talks to Immich, plus `FakeImmich` for tests |
| `src/highlights/db.py` | The only code that runs SQL |
| `src/highlights/web.py`, `templates/`, `static/` | The phone web app |

## Rules a change has to keep

These are the same rules the maintainer works to (they are also in `CLAUDE.md`).

1. **Never hard-delete from Immich.** Raw clips are only moved to Immich's trash
   (`force: false`), only when `HL_CLEANUP_ENABLED=true`, and never favorites, photos, or clips
   in another album.
2. **All SQL lives in `db.py`; all Immich calls go through `immich.py`.** If you add an Immich
   call, add it to `FakeImmich` too.
3. **Tests ship with the change.** No network in tests: use `FakeImmich` and build ffmpeg
   commands without running them. `uv run pytest -q` and `uv run ruff check .` must pass.
4. **Every segment is rendered as SDR BT.709 limited range.** The final join copies segments, so
   one odd segment breaks the whole video.
5. **Every in-app URL is built from `base`** (templates) or `request.scope["root_path"]`, because
   the app is served under a path prefix.
6. **Mobile first.** Actions sit in the bottom bar, touch targets are at least 44 px, and pages
   are checked at 375 px wide.
7. **Never commit anything real.** No hostnames, addresses, API keys, tokens, or photos of real
   people. Screenshots use the demo data described in `docs/screenshots/CREDITS.md`.
8. **Plain language, no em dashes** in UI copy, docs, and commit messages.

## Pull requests

- One change per pull request, on a branch off `main`.
- Say what you changed, why, and how you tested it. For a UI change, add a phone-width
  screenshot made with demo data.
- CI runs lint, tests, a Docker build, and a secret scan. All of them need to pass.

## Using AI tools

Most of this project was written with Claude Code, and AI-assisted contributions are welcome. The
bar is the same either way: you have read and understood the change, it has tests, and you ran
it. Say in the pull request if a tool wrote most of it.

## License

Highlights is licensed under [AGPL-3.0](LICENSE). By contributing you agree that your contribution
is licensed under the same terms.
