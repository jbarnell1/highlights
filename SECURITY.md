# Security

Highlights has no login of its own. Run it only on a private network (for example a Tailscale
tailnet) or behind a reverse proxy that authenticates. It holds an Immich API key with full
access and a Claude Code token; keep `.env` readable only by the account that runs it.

Report a vulnerability through GitHub's private vulnerability reporting on this repository
(Security > Report a vulnerability), not in a public issue.
