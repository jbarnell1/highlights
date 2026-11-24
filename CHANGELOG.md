# Changelog

What changed in each release, newest first. Versions follow [semantic versioning](https://semver.org).
A `v*` tag publishes the matching image to `ghcr.io/jbarnell1/highlights`.

## 0.2.1 (2026-11-23)

Upgrade if you run the 0.2.0 image. `docker compose pull && docker compose up -d` is all it takes;
the database layout did not change.

### Security

- **Claude Code is confined to the contact sheets.** In 0.2.0 the picking step could read any file
  the container could, including a mounted photo library, and it inherited the container's
  environment, the Immich API key among them. It now runs in a temporary folder with a read rule
  limited to that folder, with Glob and Grep turned off, and its environment drops `IMMICH_*`,
  `HL_*`, `ANTHROPIC_*` and anything named like a key, token, secret or password. See D-007 in
  [docs/DECISIONS.md](docs/DECISIONS.md).

### Fixed

- A data folder moved from Linux to Windows keeps its old absolute paths working. Stored paths
  such as `/srv/old/work/...` were read as relative on Windows.

### Documentation

- README rebuilt for people who are not the maintainer: what it is, a quick start, exactly what
  leaves your server, screenshots from a demo library, and how it was built.
- New sections on upgrading, backing up the data folder, and putting a login in front of the app.
- The project is now in maintenance. [docs/ROADMAP.md](docs/ROADMAP.md) says what that covers.
- Community files: contributing guide, code of conduct, security policy, issue templates.

## 0.2.0 (2026-11-14)

First public release.

- Finds trips and finished months in an Immich library.
- Claude picks clips and photos from contact sheets; the picks become an Immich album.
- Renders a 1080p video with NVENC, Intel Quick Sync or the CPU, and uploads it to Immich.
- Optional cleanup that moves raw clips to Immich's trash, off by default.
- A phone web app to follow each event, and a Docker image for linux/amd64.
