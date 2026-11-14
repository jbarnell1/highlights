"""Entry point: `hl serve` runs the web app and the worker; the rest are for checking setup."""

from __future__ import annotations

import argparse
import shutil
import sys

from . import db
from .config import ENV_FILE, settings


def build_pipeline():
    from .immich import Immich
    from .pipeline import Pipeline

    immich = Immich(settings.immich_url, settings.immich_api_key, settings.immich_media_root)
    from .picker import ClaudeCode

    claude = None
    if settings.claude_token:
        settings.work_dir.mkdir(parents=True, exist_ok=True)
        claude = ClaudeCode(settings.claude_path, settings.claude_token, settings.model,
                            settings.work_dir)
    return Pipeline(settings, immich, claude)


def serve(port: int) -> None:
    import uvicorn

    from .web import create_app
    from .worker import Worker

    db.init(settings.db_path)
    pipeline = build_pipeline()
    if not settings.missing():
        Worker(pipeline).start()
    else:
        print(f"Worker not started; missing settings: {', '.join(settings.missing())}")
    app = create_app(settings, pipeline)
    uvicorn.run(app, host=settings.host, port=port, root_path=settings.base_path,
                proxy_headers=True, log_level="warning")


def check() -> int:
    from .media import detect_encoder

    ok = True
    print(f"Settings file: {ENV_FILE}")
    for name in settings.missing():
        print(f"  missing {name}")
        ok = False
    print(f"Encoder: {detect_encoder(settings.ffmpeg, settings.qsv_device)} ({settings.ffmpeg})")
    if settings.immich_api_key:
        pipeline = build_pipeline()
        try:
            me = pipeline.immich.me()
            print(f"Immich: signed in as {me.get('name') or me.get('email')}")
        except Exception as e:  # noqa: BLE001
            print(f"Immich: {e}")
            ok = False
    root = settings.immich_media_root
    if root:
        print(f"Immich originals: {root} (exists: {root.exists()})")
    else:
        print("Immich originals: not mounted, clips are downloaded through the API")
    claude = shutil.which(str(settings.claude_path)) or (
        str(settings.claude_path) if settings.claude_path.exists() else None)
    print(f"Claude Code: {claude or f'not found ({settings.claude_path})'}")
    if not claude:
        ok = False
    print(f"Data folder: {settings.data_dir.resolve()}")
    print(f"Cleanup enabled: {settings.cleanup_enabled}")
    return 0 if ok else 1


def main() -> None:
    parser = argparse.ArgumentParser(prog="hl")
    sub = parser.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve", help="run the PWA and the background worker")
    s.add_argument("--port", type=int, default=8040)
    sub.add_parser("check", help="confirm settings, Immich access and the encoder")
    args = parser.parse_args()
    if args.cmd == "serve":
        serve(args.port)
    elif args.cmd == "check":
        sys.exit(check())


if __name__ == "__main__":
    main()
