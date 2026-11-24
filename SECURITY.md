# Security

Highlights has no login of its own. Run it only on a private network (for example a Tailscale
tailnet) or behind a reverse proxy that authenticates. It holds an Immich API key with full
access and a Claude Code token; keep `.env` readable only by the account that runs it.

The README has a section on [keeping it private](README.md#keeping-it-private).

## Supported versions

Only the newest release gets security fixes. If you run the 0.2.0 image, upgrade: 0.2.1 confines
the picking step to the contact sheets (see the [changelog](CHANGELOG.md)).

## Reporting a vulnerability

Report a vulnerability through GitHub's private vulnerability reporting on this repository
(Security > Report a vulnerability), not in a public issue.
