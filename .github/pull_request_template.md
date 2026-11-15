## What this changes

<!-- One or two sentences. Link the issue if there is one. -->

## Why

## How it was tested

<!-- Commands you ran, and what you checked by hand. For a UI change, add a phone-width
     screenshot made with demo data (never a real library). -->

## Checklist

- [ ] `uv run pytest -q` and `uv run ruff check .` pass
- [ ] Tests added or updated for the change
- [ ] No real hostnames, addresses, keys, tokens or personal photos in the diff
- [ ] SQL stays in `db.py`; Immich calls stay in `immich.py` (and `FakeImmich` matches)
- [ ] Nothing hard-deletes from Immich
- [ ] Docs updated if behavior or settings changed (README, `.env.example`, `docs/DECISIONS.md`)
